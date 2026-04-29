"""Gmail connector — OAuth and message fetching."""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']


def _build_service(access_token: str, refresh_token: str) -> Any:
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )
    return build('gmail', 'v1', credentials=creds, cache_discovery=False)


def list_messages(
    access_token: str,
    refresh_token: str,
    query: str = 'is:unread',
    max_results: int = 50,
) -> List[Dict]:
    """List Gmail message IDs matching query."""
    service = _build_service(access_token, refresh_token)
    messages = []
    page_token = None

    while len(messages) < max_results:
        kwargs: Dict[str, Any] = {
            'userId': 'me',
            'q': query,
            'maxResults': min(max_results - len(messages), 100),
        }
        if page_token:
            kwargs['pageToken'] = page_token

        response = service.users().messages().list(**kwargs).execute()
        messages.extend(response.get('messages', []))

        page_token = response.get('nextPageToken')
        if not page_token:
            break

    return messages


def get_message(access_token: str, refresh_token: str, message_id: str) -> Dict:
    """Fetch full message content."""
    service = _build_service(access_token, refresh_token)
    return service.users().messages().get(
        userId='me', id=message_id, format='full'
    ).execute()


def is_company_email(email: str, allowed_domains: List[str]) -> bool:
    """Check if an email belongs to an allowed company domain."""
    if not allowed_domains:
        return True  # No restriction configured
    domain = email.split('@')[-1].lower() if '@' in email else ''
    return domain in allowed_domains
