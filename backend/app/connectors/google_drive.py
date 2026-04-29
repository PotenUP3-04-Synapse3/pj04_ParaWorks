"""Google Drive connector — OAuth, file listing, download, and webhook management."""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io

from app.core.config import settings
from app.core.security import decrypt_token, encrypt_token

logger = logging.getLogger(__name__)

# OAuth2 scopes (read-only — no write permission needed)
SCOPES = [
    'https://www.googleapis.com/auth/drive.readonly',
    'https://www.googleapis.com/auth/drive.metadata.readonly',
]

# Drive → permission_level mapping
_ROLE_TO_LEVEL = {
    'owner': 'restricted',
    'organizer': 'restricted',
    'fileOrganizer': 'team',
    'writer': 'team',
    'commenter': 'team',
    'reader': 'public',
}

# Google Workspace MIME types → export MIME
_EXPORT_MIME = {
    'application/vnd.google-apps.document': 'text/markdown',
    'application/vnd.google-apps.spreadsheet': 'text/csv',
    'application/vnd.google-apps.presentation': 'text/plain',
}


def _build_service(access_token: str, refresh_token: str) -> Any:
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )
    return build('drive', 'v3', credentials=creds, cache_discovery=False)


def get_start_page_token(access_token: str, refresh_token: str) -> str:
    """Retrieve the initial page token for incremental sync."""
    service = _build_service(access_token, refresh_token)
    response = service.changes().getStartPageToken().execute()
    return response['startPageToken']


def register_watch_channel(
    access_token: str,
    refresh_token: str,
    channel_id: Optional[str] = None,
) -> Dict[str, str]:
    """Register a changes.watch channel. Returns channel metadata."""
    service = _build_service(access_token, refresh_token)
    channel_id = channel_id or str(uuid.uuid4())
    expire_ms = int((datetime.now(timezone.utc) + timedelta(days=6)).timestamp() * 1000)

    body = {
        'id': channel_id,
        'type': 'web_hook',
        'address': settings.DRIVE_WEBHOOK_ADDRESS,
        'token': settings.DRIVE_WEBHOOK_TOKEN,
        'expiration': expire_ms,
    }

    # Get current page token first
    token_resp = service.changes().getStartPageToken().execute()
    page_token = token_resp['startPageToken']

    resp = service.changes().watch(pageToken=page_token, body=body).execute()
    return {
        'channel_id': resp['id'],
        'resource_id': resp['resourceId'],
        'expiration': resp.get('expiration', ''),
        'page_token': page_token,
    }


def stop_watch_channel(
    access_token: str,
    refresh_token: str,
    channel_id: str,
    resource_id: str,
) -> None:
    """Stop an existing watch channel."""
    service = _build_service(access_token, refresh_token)
    service.channels().stop(body={'id': channel_id, 'resourceId': resource_id}).execute()


def list_changes(
    access_token: str,
    refresh_token: str,
    page_token: str,
) -> Tuple[List[Dict], str]:
    """
    Retrieve all changes since page_token.
    Returns (changes_list, new_start_page_token).
    """
    service = _build_service(access_token, refresh_token)
    changes = []

    while True:
        response = service.changes().list(
            pageToken=page_token,
            includeItemsFromAllDrives=True,
            supportsAllDrives=True,
            fields='nextPageToken,newStartPageToken,changes(fileId,removed,file(id,name,mimeType,capabilities,modifiedTime,owners,md5Checksum,trashed,parents))',
        ).execute()

        changes.extend(response.get('changes', []))

        if 'nextPageToken' in response:
            page_token = response['nextPageToken']
        else:
            return changes, response.get('newStartPageToken', page_token)


def download_file(
    access_token: str,
    refresh_token: str,
    file_id: str,
    mime_type: str,
) -> Tuple[bytes, str]:
    """
    Download a Drive file. Returns (content_bytes, actual_mime_type).
    Google Workspace files are exported; binary files are downloaded directly.
    """
    service = _build_service(access_token, refresh_token)

    # Check file size for Google Workspace exports
    if mime_type in _EXPORT_MIME:
        export_mime = _EXPORT_MIME[mime_type]
        request = service.files().export_media(fileId=file_id, mimeType=export_mime)
        actual_mime = export_mime
    else:
        request = service.files().get_media(fileId=file_id)
        actual_mime = mime_type

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    return buf.getvalue(), actual_mime


def get_file_permission_level(file_meta: Dict) -> str:
    """Map Drive file capabilities to app permission_level."""
    caps = file_meta.get('capabilities', {})
    if not caps.get('canRead', False):
        return 'none'  # Do not ingest
    if caps.get('canShare', False):
        return 'restricted'
    if caps.get('canEdit', False):
        return 'team'
    return 'public'
