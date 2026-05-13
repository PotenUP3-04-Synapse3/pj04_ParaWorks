import httpx

from backend.app.assistant.gmail_sender import (
    GMAIL_SEND_SCOPE,
    GmailDraftSender,
    GmailSendError,
)
from backend.app.connectors.slack_oauth import LocalTokenVault
from backend.app.core.config import Settings
from backend.app.models import IntegrationConnection


class FakeGmailHttpClient:
    def __init__(self, *, send_status_code: int = 200) -> None:
        self.send_status_code = send_status_code
        self.posts: list[tuple[str, dict]] = []

    def post(self, url: str, **kwargs):
        self.posts.append((url, kwargs))
        if url == 'https://oauth2.googleapis.com/token':
            return httpx.Response(200, json={'access_token': 'ya29.access'}, request=httpx.Request('POST', url))
        if url == 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send':
            return httpx.Response(
                self.send_status_code,
                json={'id': 'gmail-message-1'} if self.send_status_code < 400 else {'error': {'message': 'denied'}},
                request=httpx.Request('POST', url),
            )
        raise AssertionError(f'unexpected URL: {url}')


def test_gmail_draft_sender_refreshes_token_and_sends_message(db_session, tmp_path) -> None:
    vault = LocalTokenVault(storage_path=str(tmp_path / 'tokens.json'))
    token_ref = vault.store_token(
        connector_type='gmail',
        workspace_id='google-user-1',
        token='refresh-token-1',
        token_kind='oauth',
    )
    db_session.add(
        IntegrationConnection(
            connector_type='gmail',
            workspace_id='google-user-1',
            workspace_name='sender@example.com',
            scopes=['https://www.googleapis.com/auth/gmail.readonly', GMAIL_SEND_SCOPE],
            token_ref=token_ref,
            masked_bot_token='ref...n-1',
            status='connected',
            raw_metadata={'token_kind': 'refresh_token'},
        )
    )
    db_session.commit()
    http_client = FakeGmailHttpClient()

    result = GmailDraftSender(
        settings=Settings(google_client_id='G123', google_client_secret='S123'),
        token_vault=vault,
        http_client=http_client,
    ).send(
        db=db_session,
        to=['recipient@example.com'],
        subject='회의 취소 안내',
        body='안녕하세요.\n\n오늘 회의가 취소되었습니다.\n\n감사합니다.',
    )

    assert result.message_id == 'gmail-message-1'
    assert [url for url, _ in http_client.posts] == [
        'https://oauth2.googleapis.com/token',
        'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
    ]


def test_gmail_draft_sender_reports_gmail_api_failures(db_session, tmp_path) -> None:
    vault = LocalTokenVault(storage_path=str(tmp_path / 'tokens.json'))
    token_ref = vault.store_token(
        connector_type='gmail',
        workspace_id='google-user-1',
        token='refresh-token-1',
        token_kind='oauth',
    )
    db_session.add(
        IntegrationConnection(
            connector_type='gmail',
            workspace_id='google-user-1',
            workspace_name='sender@example.com',
            scopes=[GMAIL_SEND_SCOPE],
            token_ref=token_ref,
            masked_bot_token='ref...n-1',
            status='connected',
            raw_metadata={'token_kind': 'refresh_token'},
        )
    )
    db_session.commit()

    try:
        GmailDraftSender(
            settings=Settings(google_client_id='G123', google_client_secret='S123'),
            token_vault=vault,
            http_client=FakeGmailHttpClient(send_status_code=403),
        ).send(
            db=db_session,
            to=['recipient@example.com'],
            subject='회의 취소 안내',
            body='안녕하세요.',
        )
    except GmailSendError as exc:
        assert str(exc) == 'gmail_api_send_failed:403'
    else:
        raise AssertionError('Gmail API failure should be reported as GmailSendError')
