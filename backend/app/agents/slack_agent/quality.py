from dataclasses import dataclass


@dataclass(frozen=True)
class SlackWorkSignal:
    is_reviewable: bool
    reason: str
    reasons: tuple[str, ...]
    score: int


_LOW_CONTEXT_PHRASES = (
    '부탁드립니다',
    '부탁드려요',
    '부탁해요',
    '확인했습니다',
    '확인했어요',
    '확인 완료',
    '감사합니다',
    '고맙습니다',
    '수고하셨습니다',
    '넵',
    '네',
    '예',
    '후',
    '하...',
    '음',
)

_WORK_OBJECT_KEYWORDS = (
    'api',
    'celery',
    'evidence',
    'ir',
    'job',
    'llm',
    'mvp',
    'pgvector',
    'postgres',
    'project',
    'queue',
    'rag',
    'redis',
    'review queue',
    'slack',
    'status',
    'worker',
    'workers',
    '계약',
    '고객',
    '비용',
    '문서',
    '파일',
    '자료',
    '제안서',
    '정산',
    '견적',
    '투자',
    '유치',
    '장애',
    '버그',
    '배포',
    '일정',
    '상한',
    '프로젝트',
    '회의',
    '보고서',
    '화면',
    '기능',
    '권한',
    '데이터',
    '동기화',
    '검토사항',
)

_WORK_ACTION_KEYWORDS = (
    '검토',
    '작성',
    '공유',
    '배포',
    '수정',
    '승인',
    '회신',
    '준비',
    '진행',
    '완료',
    '결정',
    '정리',
    '업데이트',
    '전달',
    '확인 요청',
    '사용',
    '테스트',
    '분석',
    '등록',
    '처리',
    'complete',
    'confirm',
    'follow-up',
    'keeps',
    'publish',
    'reject',
    'remains',
    'use',
    'used',
    'verify',
)

_DUE_CONTEXT_KEYWORDS = (
    '오늘',
    '내일',
    '이번 주',
    '다음 주',
    '금요일',
    '목요일',
    '수요일',
    '화요일',
    '월요일',
    '까지',
    '마감',
    '기한',
    '오전',
    '오후',
)


def classify_slack_work_signal(text: str) -> SlackWorkSignal:
    normalized = ' '.join((text or '').strip().lower().split())
    if not normalized:
        return SlackWorkSignal(False, 'empty', (), 0)

    reasons: list[str] = []
    has_work_object = any(keyword in normalized for keyword in _WORK_OBJECT_KEYWORDS)
    has_work_action = any(keyword in normalized for keyword in _WORK_ACTION_KEYWORDS)
    has_due_context = any(keyword in normalized for keyword in _DUE_CONTEXT_KEYWORDS)
    has_low_context_phrase = _is_low_context_phrase(normalized)

    if has_work_object:
        reasons.append('work_object')
    if has_work_action:
        reasons.append('work_action')
    if has_due_context:
        reasons.append('due_context')

    score = len(reasons) * 20
    if has_low_context_phrase:
        score -= 20

    if has_work_object and (has_work_action or has_due_context):
        return SlackWorkSignal(True, 'work_signal', tuple(reasons), score)
    if has_work_action and has_due_context and len(normalized) >= 20:
        return SlackWorkSignal(True, 'work_signal', tuple(reasons), score)
    if has_low_context_phrase:
        return SlackWorkSignal(False, 'low_context_request', tuple(reasons), score)
    if not has_work_object:
        return SlackWorkSignal(False, 'no_work_object', tuple(reasons), score)
    return SlackWorkSignal(False, 'insufficient_work_signal', tuple(reasons), score)


def should_include_slack_message_for_review(text: str) -> bool:
    return classify_slack_work_signal(text).is_reviewable


def _is_low_context_phrase(normalized: str) -> bool:
    compact = normalized.strip(' .,!?\n\t')
    return any(compact == phrase or compact.startswith(f'{phrase}.') for phrase in _LOW_CONTEXT_PHRASES)
