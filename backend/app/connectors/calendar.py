"""Google Calendar connector — OAuth and event listing."""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def _build_service(access_token: str, refresh_token: str) -> Any:
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=settings.GOOGLE_CLIENT_ID,
        client_secret=settings.GOOGLE_CLIENT_SECRET,
        scopes=SCOPES,
    )
    return build('calendar', 'v3', credentials=creds, cache_discovery=False)


def list_events(
    access_token: str,
    refresh_token: str,
    calendar_id: str = 'primary',
    time_min: Optional[datetime] = None,
    time_max: Optional[datetime] = None,
    max_results: int = 50,
) -> List[Dict]:
    """List calendar events in a time range."""
    service = _build_service(access_token, refresh_token)

    kwargs: Dict[str, Any] = {
        'calendarId': calendar_id,
        'maxResults': max_results,
        'singleEvents': True,
        'orderBy': 'startTime',
    }

    if time_min:
        kwargs['timeMin'] = time_min.replace(tzinfo=timezone.utc).isoformat()
    else:
        kwargs['timeMin'] = datetime.now(timezone.utc).isoformat()

    if time_max:
        kwargs['timeMax'] = time_max.replace(tzinfo=timezone.utc).isoformat()

    try:
        response = service.events().list(**kwargs).execute()
        return response.get('items', [])
    except Exception as exc:
        logger.error('Calendar list_events failed: %s', exc)
        return []


def format_event_text(event: Dict) -> str:
    """Convert a Calendar event dict to text for embedding."""
    title = event.get('summary', 'untitled')
    start = event.get('start', {}).get('dateTime', event.get('start', {}).get('date', ''))
    end = event.get('end', {}).get('dateTime', event.get('end', {}).get('date', ''))
    description = event.get('description', '')
    attendees = ', '.join(
        a.get('email', '') for a in event.get('attendees', [])
    )

    parts = [f'제목: {title}', f'일시: {start} ~ {end}']
    if description:
        parts.append(f'내용: {description}')
    if attendees:
        parts.append(f'참석자: {attendees}')

    return '\n'.join(parts)
