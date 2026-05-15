from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from backend.app.assistant.recipient_resolver import RecipientResolution

CONTACT_LOOKUP_TERMS = (
    '이메일',
    '메일 주소',
    '메일주소',
    'email',
    '연락처',
    'contact',
)
CONTACT_ASK_TERMS = ('알려', '찾아', '확인', '뭐', '무엇', '주소', '조회')
EMAIL_ACTION_TERMS = (
    '보내',
    '전송',
    '발송',
    '작성',
    '초안',
    '써줘',
    'send',
    'draft',
    'compose',
    'forward',
    'reply',
)
CONTACT_LOOKUP_FOLLOWUP_TERMS = (
    '너가 알려',
    '네가 알려',
    '니가 알려',
    '알려줘야지',
    '찾아줘야지',
    '너가 찾아',
    '네가 찾아',
)


@dataclass(frozen=True)
class ContactLookupRequest:
    is_lookup: bool
    lookup_query: str = ''
    reason: str = ''


def detect_contact_lookup_request(*, latest_message: str, conversation_context: str) -> ContactLookupRequest:
    message = latest_message.strip()
    if _is_direct_contact_lookup(message):
        return ContactLookupRequest(is_lookup=True, lookup_query=message, reason='direct_lookup')

    if _is_contact_lookup_followup(message):
        recent_lookup_query = _recent_contact_lookup_query(conversation_context)
        if recent_lookup_query:
            return ContactLookupRequest(
                is_lookup=True,
                lookup_query=recent_lookup_query,
                reason='followup_lookup',
            )

    return ContactLookupRequest(is_lookup=False)


def contact_lookup_response_content(resolution: RecipientResolution) -> str:
    if resolution.status == 'resolved':
        if len(resolution.candidates) == 1:
            candidate = resolution.candidates[0]
            display_name = candidate.display_name if candidate.display_name != candidate.email else ''
            if display_name:
                return f'{display_name}님의 이메일 주소는 {candidate.email}입니다.'
            return f'확인된 이메일 주소는 {candidate.email}입니다.'
        lines = [
            _candidate_line(candidate)
            for candidate in resolution.candidates
        ]
        return '확인된 이메일 주소는 다음과 같습니다.\n' + '\n'.join(lines)

    if resolution.status == 'ambiguous':
        lines = [
            _candidate_line(candidate)
            for candidate in resolution.candidates[:5]
        ]
        return '동명이인이 있어 어느 연락처인지 확정하기 어렵습니다.\n' + '\n'.join(lines)

    if resolution.candidates:
        lines = [
            _candidate_line(candidate)
            for candidate in resolution.candidates[:3]
        ]
        return '정확히 일치하는 연락처를 찾지 못했습니다. 가까운 후보는 다음과 같습니다.\n' + '\n'.join(lines)

    return '현재 확인 가능한 연락처에서 해당 이메일 주소를 찾지 못했습니다.'


def _is_direct_contact_lookup(message: str) -> bool:
    normalized = message.lower()
    has_lookup_term = any(term.lower() in normalized for term in CONTACT_LOOKUP_TERMS)
    has_ask_term = any(term.lower() in normalized for term in CONTACT_ASK_TERMS)
    has_action_term = any(term.lower() in normalized for term in EMAIL_ACTION_TERMS)
    return has_lookup_term and has_ask_term and not has_action_term


def _is_contact_lookup_followup(message: str) -> bool:
    normalized = message.lower()
    return any(term.lower() in normalized for term in CONTACT_LOOKUP_FOLLOWUP_TERMS)


def _recent_contact_lookup_query(conversation_context: str) -> str:
    # 최근 사용자 발화 중 연락처 조회 요청만 재사용해서 후속 답변이 메일 작성 플로우로 새지 않게 한다.
    for row in reversed(_conversation_rows(conversation_context)):
        if str(row.get('role', '')) != 'user':
            continue
        content = str(row.get('content', '')).strip()
        if _is_direct_contact_lookup(content):
            return content
    return ''


def _conversation_rows(conversation_context: str) -> list[dict[str, Any]]:
    try:
        parsed = json.loads(conversation_context or '[]')
    except json.JSONDecodeError:
        return []
    if not isinstance(parsed, list):
        return []
    return [
        row
        for row in parsed
        if isinstance(row, dict)
    ]


def _candidate_line(candidate) -> str:
    label = candidate.display_name if candidate.display_name != candidate.email else candidate.email
    if label == candidate.email:
        return f'- {candidate.email}'
    return f'- {label}: {candidate.email}'
