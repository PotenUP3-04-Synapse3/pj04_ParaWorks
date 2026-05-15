import re
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agents.slack_agent.quality import classify_slack_work_signal
from backend.app.models import DocumentChunk, Project, ReviewItem, Source


@dataclass(frozen=True)
class CanonicalProject:
    project_key: str
    name: str
    summary: str
    aliases: tuple[str, ...]


CANONICAL_PROJECTS: tuple[CanonicalProject, ...] = ()

NON_PROJECT_MARKERS = (
    '00_회사규정',
    '01_제품_기술',
    '회사규정',
    '사내 규정',
    '복리후생',
    '홍보 가이드',
    '보안_정책',
    '정보 보안 정책',
)

PROJECT_SOURCE_TYPES = ('gmail', 'gmail_attachment', 'drive', 'calendar', 'slack')

_GENERIC_PROJECT_ALIAS_TERMS = {
    'data',
    'drive',
    'file',
    'files',
    'gmail',
    'google',
    'google drive',
    'slack',
    'source',
    'sources',
    'summarizes',
    'timeline',
}

_AMBIGUOUS_SINGLE_TERMS = {
    '유치',
    '투자',
    '회의',
    '일정',
    '자료',
}
_TOKEN_CLASS = '0-9A-Za-z가-힣'


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


def classify_source_project(
    source: Source,
    chunks: list[DocumentChunk],
    projects: list[Project] | None = None,
) -> ProjectAssignmentCandidate | None:
    haystack = _source_haystack(source, chunks)
    lowered = haystack.lower()
    if any(marker.lower() in lowered for marker in NON_PROJECT_MARKERS):
        return None

    matched_project: Project | None = None
    matched_alias = ''
    for project in projects or []:
        for alias in _project_aliases(project):
            if _contains_alias(lowered, alias):
                matched_project = project
                matched_alias = alias
                break
        if matched_project is not None:
            break

    if matched_project is None:
        return None
    if source.source_type == 'slack' and not _has_reviewable_slack_signal(source, chunks):
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
    projects = db.scalars(select(Project).order_by(Project.created_at.desc(), Project.id.desc())).all()
    if not projects:
        return []

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
    return [
        candidate
        for source in sources
        if (candidate := classify_source_project(source, chunks_by_source.get(source.id, []), projects)) is not None
    ]


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


def _project_aliases(project: Project) -> tuple[str, ...]:
    raw_aliases = [project.name, project.project_key.replace('project-', '').replace('-', ' ')]
    raw_aliases.extend(_meaningful_terms(project.name))
    raw_aliases.extend(_meaningful_terms(project.summary))
    seen: set[str] = set()
    aliases: list[str] = []
    for alias in raw_aliases:
        normalized = ' '.join(alias.split()).strip()
        if len(normalized) < 2:
            continue
        key = normalized.lower()
        if normalized in _AMBIGUOUS_SINGLE_TERMS or key in _GENERIC_PROJECT_ALIAS_TERMS:
            continue
        if key in seen:
            continue
        seen.add(key)
        aliases.append(normalized)
    return tuple(aliases)


def _meaningful_terms(text: str) -> list[str]:
    terms = re.findall(r'[0-9A-Za-z가-힣]{2,}', text)
    stopwords = {
        '프로젝트',
        '업무',
        '진행',
        '상태',
        '고객',
        '문서',
        '계약',
        '이번',
        '관련',
        '확인',
        '개편',
        '활동',
        '관리',
    }
    return [
        term
        for term in terms
        if term.lower() not in stopwords
        and term.lower() not in _GENERIC_PROJECT_ALIAS_TERMS
        and term not in _AMBIGUOUS_SINGLE_TERMS
    ]


def _contains_alias(lowered_haystack: str, alias: str) -> bool:
    normalized_haystack = ' '.join(lowered_haystack.split())
    normalized_alias = ' '.join(alias.lower().split())
    if normalized_alias in {'ir', 'vc'}:
        return re.search(rf'(?<![0-9a-z]){re.escape(normalized_alias)}(?![0-9a-z])', normalized_haystack) is not None
    alias_pattern = re.escape(normalized_alias).replace(r'\ ', r'\s+')
    return re.search(rf'(?<![{_TOKEN_CLASS}]){alias_pattern}(?![{_TOKEN_CLASS}])', normalized_haystack) is not None


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


def _has_reviewable_slack_signal(source: Source, chunks: list[DocumentChunk]) -> bool:
    signal_texts = [_slack_message_signal_text(chunk.source_snippet or chunk.text) for chunk in chunks]
    signal_texts = [text for text in signal_texts if text]
    if not signal_texts and source.title:
        signal_texts.append(source.title)
    return any(classify_slack_work_signal(text).is_reviewable for text in signal_texts)


def _slack_message_signal_text(text: str) -> str:
    cleaned = (text or '').strip()
    if not cleaned:
        return ''
    marker = 'Thread reply:'
    if marker in cleaned:
        return cleaned.rsplit(marker, maxsplit=1)[-1].strip()
    return cleaned


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
