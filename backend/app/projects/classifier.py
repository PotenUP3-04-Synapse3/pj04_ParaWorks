import re
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import DocumentChunk, ReviewItem, Source


@dataclass(frozen=True)
class CanonicalProject:
    project_key: str
    name: str
    summary: str
    aliases: tuple[str, ...]


CANONICAL_PROJECTS = (
    CanonicalProject(
        project_key='k-tech-pilot',
        name='K테크 파일럿',
        summary='K테크 솔루션즈 엔터프라이즈 파일럿 계약, 온보딩, 검증 일정을 추적합니다.',
        aliases=('k테크', 'k-tech', 'ktech', '파일럿', '02_파일럿_프로젝트', '엔터프라이즈 파일럿'),
    ),
    CanonicalProject(
        project_key='seed-ir',
        name='시드 투자 IR',
        summary='시드 투자 IR, 투자자 커뮤니케이션, 재무/피치덱 준비 흐름을 추적합니다.',
        aliases=('ir', '투자', 'series seed', 'seed', '03_ir_투자', '피치덱', 'vc', '밸류에이션'),
    ),
)

NON_PROJECT_MARKERS = (
    '00_회사규정',
    '01_제품_기술',
    '회사규정',
    '사내 규정',
    '복리후생',
    '온보딩 가이드',
    '보안_정책',
    '정보 보안 정책',
)

PROJECT_SOURCE_TYPES = ('gmail', 'gmail_attachment', 'drive', 'calendar', 'slack')


@dataclass(frozen=True)
class ProjectAssignmentCandidate:
    project_key: str
    project_name: str
    source_id: str
    source_type: str
    source_url: str
    source_title: str
    source_snippet: str
    permission_level: str
    confidence_score: float
    evidence_reason: str
    task_summary: str
    timestamp: str


def classify_source_project(source: Source, chunks: list[DocumentChunk]) -> ProjectAssignmentCandidate | None:
    haystack = _source_haystack(source, chunks)
    lowered = haystack.lower()
    if any(marker.lower() in lowered for marker in NON_PROJECT_MARKERS):
        return None

    matched_project: CanonicalProject | None = None
    matched_alias = ''
    for project in CANONICAL_PROJECTS:
        for alias in project.aliases:
            if _contains_alias(lowered, alias):
                matched_project = project
                matched_alias = alias
                break
        if matched_project is not None:
            break

    if matched_project is None:
        return None

    snippet = _best_snippet(source, chunks)
    return ProjectAssignmentCandidate(
        project_key=matched_project.project_key,
        project_name=matched_project.name,
        source_id=source.source_id,
        source_type=source.source_type,
        source_url=source.source_url,
        source_title=source.title,
        source_snippet=snippet,
        permission_level=_strictest_permission([source.permission_level, *(chunk.permission_level for chunk in chunks)]),
        confidence_score=0.88,
        evidence_reason=f'"{matched_alias}" 단서가 source 제목/본문/메타데이터에서 발견되었습니다.',
        task_summary=_task_summary(source, snippet),
        timestamp=_source_timestamp(source),
    )


def build_project_assignment_candidates(db: Session) -> list[ProjectAssignmentCandidate]:
    sources = db.scalars(
        select(Source)
        .where(Source.source_type.in_(PROJECT_SOURCE_TYPES))
        .order_by(Source.created_at.desc(), Source.id.desc())
    ).all()
    chunks_by_source: dict[int, list[DocumentChunk]] = {
        source.id: db.scalars(
            select(DocumentChunk).where(DocumentChunk.source_id == source.id).order_by(DocumentChunk.chunk_index)
        ).all()
        for source in sources
    }
    candidates = [
        candidate
        for source in sources
        if (candidate := classify_source_project(source, chunks_by_source.get(source.id, []))) is not None
    ]
    return candidates


def create_project_assignment_review_items(db: Session) -> list[ReviewItem]:
    candidates = build_project_assignment_candidates(db)
    existing_keys = {
        _assignment_identity(item.payload)
        for item in db.scalars(select(ReviewItem).where(ReviewItem.item_type == 'project_assignment')).all()
    }
    created: list[ReviewItem] = []
    for candidate in candidates:
        identity = f'{candidate.project_key}:{candidate.source_id}'
        if identity in existing_keys:
            continue
        item = ReviewItem(
            item_type='project_assignment',
            payload={
                'agent_name': 'project_classifier',
                'title': f'{candidate.project_name} source 연결',
                'summary': candidate.task_summary,
                'project_key': candidate.project_key,
                'project_name': candidate.project_name,
                'source_id': candidate.source_id,
                'source_type': candidate.source_type,
                'source_title': candidate.source_title,
                'task_summary': candidate.task_summary,
                'evidence_reason': candidate.evidence_reason,
                'timestamp': candidate.timestamp,
            },
            source_links=[candidate.source_url],
            source_snippets=[candidate.source_snippet],
            confidence_score=candidate.confidence_score,
            permission_level=candidate.permission_level,
        )
        db.add(item)
        created.append(item)
        existing_keys.add(identity)
    return created


def project_by_key(project_key: str) -> CanonicalProject | None:
    return next((project for project in CANONICAL_PROJECTS if project.project_key == project_key), None)


def _contains_alias(lowered_haystack: str, alias: str) -> bool:
    lowered_alias = alias.lower()
    if lowered_alias in {'ir', 'vc'}:
        return re.search(rf'(?<![0-9a-z]){re.escape(lowered_alias)}(?![0-9a-z])', lowered_haystack) is not None
    return lowered_alias in lowered_haystack


def _assignment_identity(payload: dict) -> str:
    project_key = payload.get('project_key')
    source_id = payload.get('source_id')
    if isinstance(project_key, str) and isinstance(source_id, str):
        return f'{project_key}:{source_id}'
    return ''


def _source_haystack(source: Source, chunks: list[DocumentChunk]) -> str:
    metadata_values = ' '.join(str(value) for value in (source.raw_metadata or {}).values())
    chunk_text = ' '.join((chunk.source_snippet or chunk.text)[:500] for chunk in chunks[:3])
    return ' '.join([source.source_url, source.title, source.source_id, metadata_values, chunk_text])


def _best_snippet(source: Source, chunks: list[DocumentChunk]) -> str:
    for chunk in chunks:
        snippet = (chunk.source_snippet or chunk.text).strip()
        if snippet:
            return snippet[:500]
    return source.title


def _task_summary(source: Source, snippet: str) -> str:
    cleaned = ' '.join(snippet.split())
    if cleaned and cleaned != source.title:
        return cleaned[:160]
    return source.title


def _source_timestamp(source: Source) -> str:
    metadata = source.raw_metadata or {}
    for key in ('sync_cursor', 'modified_time', 'date_header'):
        value = metadata.get(key)
        if isinstance(value, str) and value:
            return value
    return (source.created_at or datetime.now(UTC)).isoformat()


PERMISSION_RANK = {'public': 0, 'internal': 1, 'restricted': 2}


def _strictest_permission(levels: list[str]) -> str:
    return max((level for level in levels if level), key=lambda level: PERMISSION_RANK.get(level, 1), default='internal')
