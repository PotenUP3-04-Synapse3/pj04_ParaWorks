import re
from dataclasses import dataclass


EMAIL_ACTION_PROMPT_VERSION = 'assistant-email-draft:v1'
EMAIL_ADDRESS_PATTERN = re.compile(r'[\w.!#$%&\'*+/=?^`{|}~-]+@[\w.-]+\.[A-Za-z]{2,}')


@dataclass(frozen=True)
class EmailDraft:
    to: list[str]
    subject: str
    body: str


def build_email_draft_from_request(content: str) -> EmailDraft | None:
    """사용자 발화가 메일 전송 요청이면 승인용 초안을 만든다."""
    normalized = ' '.join(content.strip().split())
    if not _looks_like_email_action(normalized):
        return None

    recipients = _extract_recipients(normalized)
    if not recipients:
        return None

    core_message = _extract_requested_email_body(normalized, recipients[0])
    if not core_message:
        return None

    return EmailDraft(
        to=recipients,
        subject=_business_subject(core_message),
        body=_business_body(core_message),
    )


def assistant_email_draft_content(draft: EmailDraft) -> str:
    """채팅에 보여줄 초안 본문은 사람이 승인하기 쉽게 고정 형식으로 만든다."""
    recipients = ', '.join(draft.to)
    return (
        '메일 초안을 작성했습니다. 보내기 전에 내용을 확인해 주세요.\n\n'
        f'수신자: {recipients}\n'
        f'제목: {draft.subject}\n\n'
        f'{draft.body}\n\n'
        '승인하면 연결된 Gmail 계정으로 전송합니다.'
    )


def email_draft_metadata(draft: EmailDraft) -> dict[str, object]:
    """전송 승인 버튼이 재사용할 수 있도록 초안 데이터를 메시지 metadata에 보관한다."""
    return {
        'action_type': 'email_draft',
        'status': 'pending_approval',
        'prompt_version': EMAIL_ACTION_PROMPT_VERSION,
        'email_draft': {
            'to': draft.to,
            'subject': draft.subject,
            'body': draft.body,
        },
    }


def _looks_like_email_action(content: str) -> bool:
    has_mail_word = '메일' in content or '이메일' in content
    has_send_word = any(keyword in content for keyword in ('보내', '전송', '발송'))
    return has_mail_word and has_send_word and EMAIL_ADDRESS_PATTERN.search(content) is not None


def _extract_recipients(content: str) -> list[str]:
    recipients: list[str] = []
    for match in EMAIL_ADDRESS_PATTERN.finditer(content):
        address = match.group(0).lower()
        if address not in recipients:
            recipients.append(address)
    return recipients


def _extract_requested_email_body(content: str, first_recipient: str) -> str:
    after_recipient = content.split(first_recipient, 1)[1]
    # 한국어 조사와 명령 표현을 제거해 사용자가 실제로 전달하려는 핵심 문장만 남긴다.
    cleaned = re.sub(r'^(에게|한테|에|으로|로)\s*', '', after_recipient).strip()
    cleaned = re.sub(r'(라고|이라고)?\s*(이?메일\s*)?(보내줘|보내주세요|전송해줘|전송해주세요|발송해줘|발송해주세요)[.!?。]*$', '', cleaned)
    cleaned = cleaned.strip(' .!?。')
    if cleaned.endswith('됐다고'):
        cleaned = f'{cleaned[:-3].rstrip()}되었습니다'
    return cleaned.strip()


def _business_subject(core_message: str) -> str:
    if '회의' in core_message and ('취소' in core_message or '취소되' in core_message):
        return '회의 취소 안내'
    if '회의' in core_message:
        return '회의 안내'
    summary = core_message[:18].strip()
    return f'{summary} 안내' if summary else '업무 안내'


def _business_body(core_message: str) -> str:
    sentence = core_message.rstrip('.')
    if not sentence.endswith(('습니다', '드립니다', '입니다', '됩니다')):
        sentence = f'{sentence}입니다'
    return f'안녕하세요.\n\n{sentence}.\n\n감사합니다.'
