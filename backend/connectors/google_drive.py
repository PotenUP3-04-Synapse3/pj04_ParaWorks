from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

import structlog
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload
import io

from backend.connectors.base import BaseConnector, RawDocument
from backend.core.config import settings

log = structlog.get_logger(__name__)

# 파일 ID → MIME 타입 매핑 (Google 내보내기 대상)
EXPORT_MIME_MAP: dict[str, str] = {
    'application/vnd.google-apps.document': 'text/plain',
    'application/vnd.google-apps.spreadsheet': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.google-apps.presentation': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
}

SUPPORTED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/plain',
    'text/markdown',
    'application/haansofthwp',       # HWP
    'application/x-hwp',
    'application/vnd.hancom.hwp',
    'application/vnd.hancom.hwpx',
    *EXPORT_MIME_MAP.keys(),
}


def _build_credentials():
    sa_json = settings.google_service_account_json
    if os.path.exists(sa_json):
        creds = service_account.Credentials.from_service_account_file(
            sa_json,
            scopes=['https://www.googleapis.com/auth/drive.readonly'],
        )
    else:
        info = json.loads(sa_json)
        creds = service_account.Credentials.from_service_account_info(
            info,
            scopes=['https://www.googleapis.com/auth/drive.readonly'],
        )
    return creds.with_subject(settings.google_subject_email)


class GoogleDriveConnector(BaseConnector):
    def __init__(self):
        self._service = None

    async def authenticate(self) -> None:
        creds = _build_credentials()
        self._service = build('drive', 'v3', credentials=creds, cache_discovery=False)
        log.info('google_drive.authenticated')

    def _service_or_raise(self):
        if self._service is None:
            raise RuntimeError('Call authenticate() first')
        return self._service

    async def fetch_recent(self, since: datetime | None = None) -> list[RawDocument]:
        svc = self._service_or_raise()
        query_parts = [f"mimeType != 'application/vnd.google-apps.folder'"]
        if since:
            ts = since.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
            query_parts.append(f"modifiedTime > '{ts}'")

        docs: list[RawDocument] = []
        page_token: str | None = None
        while True:
            try:
                resp = svc.files().list(
                    q=' and '.join(query_parts),
                    spaces='drive',
                    fields='nextPageToken, files(id, name, mimeType, webViewLink, modifiedTime, version)',
                    pageToken=page_token,
                    pageSize=100,
                ).execute()
            except HttpError as exc:
                log.error('google_drive.list_error', error=str(exc))
                break

            for f in resp.get('files', []):
                mime = f.get('mimeType', '')
                if mime not in SUPPORTED_MIME_TYPES:
                    continue
                content = await self._download_file(svc, f['id'], mime)
                if content is None:
                    continue
                modified_str = f.get('modifiedTime')
                modified_at = datetime.fromisoformat(modified_str.replace('Z', '+00:00')) if modified_str else None

                docs.append(RawDocument(
                    source_type='google_drive',
                    source_id=f['id'],
                    source_url=f.get('webViewLink'),
                    title=f.get('name'),
                    raw_content=content,
                    mime_type=mime,
                    version_label=str(f.get('version', '')),
                    modified_at=modified_at,
                    metadata={'drive_file_id': f['id']},
                ))

            page_token = resp.get('nextPageToken')
            if not page_token:
                break

        log.info('google_drive.fetched', count=len(docs))
        return docs

    async def _download_file(self, svc, file_id: str, mime_type: str) -> bytes | None:
        try:
            export_mime = EXPORT_MIME_MAP.get(mime_type)
            if export_mime:
                request = svc.files().export_media(fileId=file_id, mimeType=export_mime)
            else:
                request = svc.files().get_media(fileId=file_id)

            buf = io.BytesIO()
            downloader = MediaIoBaseDownload(buf, request)
            done = False
            while not done:
                _, done = downloader.next_chunk()
            return buf.getvalue()
        except HttpError as exc:
            log.warning('google_drive.download_skip', file_id=file_id, error=str(exc))
            return None

    async def fetch_permissions(self, source_id: str) -> list[dict]:
        svc = self._service_or_raise()
        try:
            resp = svc.permissions().list(
                fileId=source_id,
                fields='permissions(emailAddress, role)',
            ).execute()
            return [
                {'email': p.get('emailAddress', ''), 'role': p.get('role', '')}
                for p in resp.get('permissions', [])
                if p.get('emailAddress')
            ]
        except HttpError as exc:
            log.warning('google_drive.permissions_error', file_id=source_id, error=str(exc))
            return []

    async def get_file_revisions(self, file_id: str) -> list[dict[str, Any]]:
        """문서 버전 히스토리 조회."""
        svc = self._service_or_raise()
        try:
            resp = svc.revisions().list(
                fileId=file_id,
                fields='revisions(id, modifiedTime, lastModifyingUser)',
            ).execute()
            return resp.get('revisions', [])
        except HttpError as exc:
            log.warning('google_drive.revisions_error', file_id=file_id, error=str(exc))
            return []
