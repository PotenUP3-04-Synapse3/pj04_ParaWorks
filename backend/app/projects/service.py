import re
from collections import defaultdict
from dataclasses import dataclass
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import DocumentChunk, Source

PROJECT_SOURCE_TYPES = ('gmail', 'gmail_attachment', 'drive', 'calendar', 'slack')
PERMISSION_RANK = {'public': 0, 'internal': 1, 'restricted': 2}
SOURCE_TYPE_RANK = {'gmail': 0, 'gmail_attachment': 1, 'drive': 2, 'calendar': 3, 'slack': 4}


@dataclass(frozen=True)
class ProjectEvidence:
    source_id: str
    source_type: str
    title: str
    source_url: str
    source_snippet: str
    permission_level: str
    timestamp: str


@dataclass(frozen=True)
class ProjectMemory:
    project_key: str
    name: str
    summary: str
    source_types: list[str]
    evidence_count: int
    permission_level: str
    latest_timestamp: str
    evidence: list[ProjectEvidence]


def build_project_memory(db: Session) -> list[ProjectMemory]:
    rows = db.execute(
        select(DocumentChunk, Source)
        .join(Source, DocumentChunk.source_id == Source.id)
        .where(Source.source_type.in_(PROJECT_SOURCE_TYPES))
        .order_by(Source.created_at.desc(), Source.id.desc(), DocumentChunk.chunk_index)
    ).all()
    grouped: dict[str, list[tuple[DocumentChunk, Source]]] = defaultdict(list)
    sorted_rows = sorted(
        rows,
        key=lambda row: (SOURCE_TYPE_RANK.get(row[1].source_type, 99), row[1].id),
    )
    for chunk, source in sorted_rows:
        grouped[_project_key(source)].append((chunk, source))

    projects = [_project_memory_from_rows(project_key, project_rows) for project_key, project_rows in grouped.items()]
    return sorted(projects, key=lambda project: (project.latest_timestamp, project.project_key), reverse=True)


def _project_memory_from_rows(project_key: str, rows: list[tuple[DocumentChunk, Source]]) -> ProjectMemory:
    evidence_by_source: dict[str, ProjectEvidence] = {}
    permission_levels: list[str] = []
    source_types: set[str] = set()
    timestamps: list[str] = []
    titles: list[str] = []

    for chunk, source in rows:
        timestamp = _source_timestamp(source)
        permission_levels.append(chunk.permission_level)
        source_types.add(source.source_type)
        timestamps.append(timestamp)
        if source.title not in titles:
            titles.append(source.title)
        evidence_by_source.setdefault(
            source.source_id,
            ProjectEvidence(
                source_id=source.source_id,
                source_type=source.source_type,
                title=source.title,
                source_url=source.source_url,
                source_snippet=chunk.source_snippet or chunk.text[:240],
                permission_level=chunk.permission_level,
                timestamp=timestamp,
            ),
        )

    evidence = sorted(
        evidence_by_source.values(),
        key=lambda item: (item.timestamp, item.source_id),
        reverse=True,
    )
    return ProjectMemory(
        project_key=project_key,
        name=_project_name(project_key),
        summary=_project_summary(titles),
        source_types=sorted(source_types),
        evidence_count=len(evidence),
        permission_level=_strictest_permission(permission_levels),
        latest_timestamp=max(timestamps) if timestamps else '',
        evidence=evidence,
    )


def _project_key(source: Source) -> str:
    metadata = source.raw_metadata or {}
    for key in ('project_key', 'scenario'):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return _slug(value)
    for value in (source.source_url, source.title, source.source_id):
        inferred = _project_slug_from_text(value)
        if inferred:
            return inferred
    return 'unclassified'


def _project_slug_from_text(value: str) -> str:
    normalized = value.lower()
    parsed = urlparse(value)
    haystack = f'{parsed.path} {normalized}' if parsed.scheme else normalized
    match = re.search(r'(project[-_\s]+[a-z0-9가-힣]+)', haystack)
    if match:
        return _slug(match.group(1))
    korean_match = re.search(r'(프로젝트[-_\s]*[a-z0-9가-힣]+)', haystack)
    if korean_match:
        return _slug(korean_match.group(1))
    return ''


def _project_name(project_key: str) -> str:
    if project_key == 'unclassified':
        return '미분류 프로젝트'
    return ' '.join(part.capitalize() for part in project_key.split('-') if part)


def _project_summary(titles: list[str]) -> str:
    title_summary = ', '.join(titles[:3]) or '수집된'
    return f'{title_summary} 증거가 하나의 프로젝트 흐름으로 묶였습니다.'


def _source_timestamp(source: Source) -> str:
    metadata = source.raw_metadata or {}
    for key in ('sync_cursor', 'modified_time', 'date_header'):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return source.created_at.isoformat()


def _strictest_permission(levels: list[str]) -> str:
    if not levels:
        return 'internal'
    return max(levels, key=lambda level: PERMISSION_RANK.get(level, 1))


def _slug(value: str) -> str:
    lowered = value.strip().lower().replace('_', '-')
    return re.sub(r'[^0-9a-z가-힣]+', '-', lowered).strip('-') or 'unclassified'
