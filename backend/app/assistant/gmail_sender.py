import base64
from dataclasses import dataclass
from email.message import EmailMessage

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.connectors.slack_oauth import LOCAL_TOKEN_VAULT, LocalTokenVault
from backend.app.core.config import Settings
from backend.app.models import IntegrationConnection

GMAIL_SEND_SCOPE = 'https://www.googleapis.com/auth/gmail.send'


class GmailSendError(RuntimeError):
    pass


@dataclass(frozen=True)
class GmailSendResult:
    message_id: str


class GmailDraftSender:
    def __init__(
        self,
        *,
        settings: Settings,
        token_vault: LocalTokenVault = LOCAL_TOKEN_VAULT,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.settings = settings
        self.token_vault = token_vault
        self.http_client = http_client or httpx.Client(timeout=30.0)

    def send(self, *, db: Session, to: list[str], subject: str, body: str) -> GmailSendResult:
        connection = _latest_connected_gmail_connection(db)
        if connection is None:
            raise GmailSendError('gmail_connection_required')
        if GMAIL_SEND_SCOPE not in connection.scopes:
            raise GmailSendError('gmail_send_scope_required')

        stored_token = self.token_vault.resolve(connection.token_ref)
        if not stored_token:
            raise GmailSendError('gmail_token_unavailable')

        access_token = self._access_token(connection=connection, stored_token=stored_token)
        try:
            response = self.http_client.post(
                'https://gmail.googleapis.com/gmail/v1/users/me/messages/send',
                headers={'Authorization': f'Bearer {access_token}'},
                json={'raw': _raw_gmail_message(to=to, subject=subject, body=body)},
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise GmailSendError(f'gmail_api_send_failed:{exc.response.status_code}') from exc
        except httpx.RequestError as exc:
            raise GmailSendError('gmail_api_send_unreachable') from exc
        payload = response.json()
        return GmailSendResult(message_id=str(payload.get('id') or 'sent'))

    def _access_token(self, *, connection: IntegrationConnection, stored_token: str) -> str:
        # OAuth 콜백에서 refresh_token을 받은 경우에는 전송 직전에 access_token으로 교환한다.
        if connection.raw_metadata.get('token_kind') != 'refresh_token':
            return stored_token
        if not self.settings.google_client_id or not self.settings.google_client_secret:
            raise GmailSendError('gmail_refresh_credentials_required')

        try:
            response = self.http_client.post(
                'https://oauth2.googleapis.com/token',
                data={
                    'client_id': self.settings.google_client_id,
                    'client_secret': self.settings.google_client_secret,
                    'grant_type': 'refresh_token',
                    'refresh_token': stored_token,
                },
            )
            response.raise_for_status()
            return str(response.json()['access_token'])
        except httpx.HTTPStatusError as exc:
            raise GmailSendError(f'gmail_refresh_failed:{exc.response.status_code}') from exc
        except (KeyError, ValueError) as exc:
            raise GmailSendError('gmail_refresh_response_invalid') from exc
        except httpx.RequestError as exc:
            raise GmailSendError('gmail_refresh_unreachable') from exc


def _latest_connected_gmail_connection(db: Session) -> IntegrationConnection | None:
    return db.scalar(
        select(IntegrationConnection)
        .where(
            IntegrationConnection.connector_type == 'gmail',
            IntegrationConnection.status == 'connected',
        )
        .order_by(IntegrationConnection.updated_at.desc(), IntegrationConnection.id.desc())
    )


def _raw_gmail_message(*, to: list[str], subject: str, body: str) -> str:
    message = EmailMessage()
    message['To'] = ', '.join(to)
    message['Subject'] = subject
    message.set_content(body)
    raw_bytes = message.as_bytes()
    return base64.urlsafe_b64encode(raw_bytes).decode().rstrip('=')
