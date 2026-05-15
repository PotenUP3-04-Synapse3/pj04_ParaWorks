from dataclasses import dataclass

EMAIL_ACTION_PROMPT_VERSION = 'assistant-email-draft-composer:v1'


@dataclass(frozen=True)
class EmailDraft:
    to: list[str]
    subject: str
    body: str

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
