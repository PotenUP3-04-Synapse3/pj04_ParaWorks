from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from backend.app.assistant.email_actions import EmailDraft

REFERENCE_TERMS = (
    '이 내용',
    '위 내용',
    '위의 내용',
    '그 내용',
    '이걸',
    '그걸',
    '방금',
    '앞의',
    '최근 답변',
    'this content',
    'above',
)
SEND_TERMS = ('메일', '이메일', '보내', '전송', '발송', 'send', 'email')
REVISION_TERMS = (
    '내용',
    '본문',
    '안 들어',
    '안들어',
    '빠졌',
    '빠져',
    '없잖',
    '하나도',
    '누락',
    '수정',
    '다시',
)
EXCLUDED_ASSISTANT_ACTIONS = {
    'contact_lookup',
    'email_clarification',
}


@dataclass(frozen=True)
class PendingEmailDraft:
    to: list[str]
    subject: str
    body: str
    message_id: int | None = None

    @property
    def resolved_recipients(self) -> list[dict[str, object]]:
        return [
            {
                'email': recipient,
                'display_name': recipient,
                'title': '',
                'department': '',
                'source_type': 'pending_email_draft',
                'confidence_score': 1.0,
            }
            for recipient in self.to
        ]


@dataclass(frozen=True)
class EmailSourceContext:
    should_route: bool
    kind: str = ''
    content: str = ''
    source_message_id: int | None = None
    pending_draft: PendingEmailDraft | None = None
    reason: str = ''

    @property
    def metadata(self) -> dict[str, object]:
        return {
            'kind': self.kind,
            'source_message_id': self.source_message_id,
            'pending_draft_message_id': (
                self.pending_draft.message_id if self.pending_draft else None
            ),
            'reason': self.reason,
        }


def build_email_source_context(*, messages: list[Any], latest_message: str) -> EmailSourceContext:
    pending_draft = find_latest_pending_email_draft(messages)
    is_reference_request = _is_reference_email_request(latest_message)
    is_revision_request = pending_draft is not None and _is_draft_revision_request(latest_message)
    if not is_reference_request and not is_revision_request:
        return EmailSourceContext(should_route=False)

    artifact = find_latest_sendable_artifact(messages)
    if artifact is None:
        if pending_draft is None:
            return EmailSourceContext(should_route=False)
        return EmailSourceContext(
            should_route=True,
            kind='pending_email_draft',
            content=pending_draft.body,
            pending_draft=pending_draft,
            reason='pending_draft_revision' if is_revision_request else 'pending_draft_reference',
        )

    return EmailSourceContext(
        should_route=True,
        kind='assistant_answer',
        content=artifact['content'],
        source_message_id=artifact['message_id'],
        pending_draft=pending_draft,
        reason='draft_revision' if is_revision_request else 'referenced_assistant_answer',
    )


def find_latest_pending_email_draft(messages: list[Any]) -> PendingEmailDraft | None:
    for message in reversed(messages):
        metadata = dict(getattr(message, 'metadata_', None) or {})
        draft = metadata.get('email_draft')
        if metadata.get('action_type') != 'email_draft':
            continue
        if metadata.get('status') != 'pending_approval':
            continue
        if not isinstance(draft, dict):
            continue
        to = [str(item).strip() for item in draft.get('to', []) if str(item).strip()]
        subject = str(draft.get('subject') or '').strip()
        body = str(draft.get('body') or '').strip()
        if not to or not subject or not body:
            continue
        return PendingEmailDraft(
            to=to,
            subject=subject,
            body=body,
            message_id=getattr(message, 'id', None),
        )
    return None


def find_latest_sendable_artifact(messages: list[Any]) -> dict[str, object] | None:
    for message in reversed(messages):
        if getattr(message, 'role', '') != 'assistant':
            continue
        metadata = dict(getattr(message, 'metadata_', None) or {})
        if metadata.get('status') == 'failed':
            continue
        if metadata.get('action_type') in EXCLUDED_ASSISTANT_ACTIONS:
            continue
        if metadata.get('action_type') == 'email_draft':
            continue
        content = str(getattr(message, 'content', '')).strip()
        if not content:
            continue
        return {
            'message_id': getattr(message, 'id', None),
            'content': content,
        }
    return None


def render_email_source_context(source_context: EmailSourceContext, *, max_chars: int) -> str:
    if not source_context.content:
        return ''
    lines = [
        'Selected email body source:',
        f'kind: {source_context.kind}',
        f'reason: {source_context.reason}',
        '',
        source_context.content,
    ]
    rendered = '\n'.join(lines)
    return rendered[-max_chars:]


def merge_resolved_recipients(
    resolved_recipients: list[dict[str, object]],
    source_context: EmailSourceContext,
) -> list[dict[str, object]]:
    if resolved_recipients:
        return resolved_recipients
    if source_context.pending_draft is None:
        return []
    return source_context.pending_draft.resolved_recipients


def ensure_draft_contains_source(draft: EmailDraft, source_context: EmailSourceContext) -> EmailDraft:
    source = source_context.content.strip()
    if not source or _source_is_already_included(draft.body, source):
        return draft

    # 모델이 "이 내용"을 일반 공유 문장으로 축약하면 실제 본문이 빠지므로 선택된 산출물을 본문에 보강한다.
    body = draft.body.strip()
    body = f'{body}\n\n{source}' if body else source
    return EmailDraft(to=draft.to, subject=draft.subject, body=body)


def fallback_draft_from_source(
    *,
    source_context: EmailSourceContext,
    resolved_recipients: list[dict[str, object]],
) -> EmailDraft | None:
    recipients = [str(item.get('email') or '').strip() for item in resolved_recipients]
    recipients = [recipient for recipient in recipients if recipient]
    if not recipients or not source_context.content.strip():
        return None
    subject = source_context.pending_draft.subject if source_context.pending_draft else _fallback_subject(source_context.content)
    return EmailDraft(
        to=recipients,
        subject=subject,
        body=source_context.content.strip(),
    )


def _is_reference_email_request(message: str) -> bool:
    normalized = message.lower()
    has_reference = any(term.lower() in normalized for term in REFERENCE_TERMS)
    has_send = any(term.lower() in normalized for term in SEND_TERMS)
    return has_reference and has_send


def _is_draft_revision_request(message: str) -> bool:
    normalized = message.lower()
    return any(term.lower() in normalized for term in REVISION_TERMS)


def _source_is_already_included(body: str, source: str) -> bool:
    normalized_body = _normalize_text(body)
    source_markers = [
        _normalize_text(line)
        for line in source.splitlines()
        if len(_normalize_text(line)) >= 12
    ][:5]
    if not source_markers:
        return False
    return any(marker in normalized_body for marker in source_markers)


def _normalize_text(value: str) -> str:
    return ''.join(str(value or '').lower().split())


def _fallback_subject(source: str) -> str:
    first_line = next((line.strip() for line in source.splitlines() if line.strip()), '')
    if not first_line:
        return '공유드립니다'
    return f'{first_line[:40]} 공유드립니다'
