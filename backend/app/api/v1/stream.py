"""SSE Stream API — real-time job status updates via Server-Sent Events."""
from __future__ import annotations

import asyncio
import json
import logging
from typing import AsyncGenerator

from celery.result import AsyncResult
from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.tasks.celery_app import celery_app

router = APIRouter(prefix='/stream', tags=['stream'])
logger = logging.getLogger(__name__)

# How frequently (seconds) to poll Celery for task state
POLL_INTERVAL = 1.5
# Max streaming duration in seconds before auto-close
MAX_STREAM_SECONDS = 300


async def _task_event_generator(task_id: str) -> AsyncGenerator[str, None]:
    """Poll Celery task state and yield SSE events until terminal state."""
    elapsed = 0.0
    sent_states: set[str] = set()

    while elapsed < MAX_STREAM_SECONDS:
        try:
            result = AsyncResult(task_id, app=celery_app)
            state = result.state
            info = result.info

            payload: dict = {'task_id': task_id, 'status': state}

            if state == 'PROGRESS' and isinstance(info, dict):
                payload.update(info)
            elif state == 'SUCCESS':
                payload['result'] = str(info)[:500] if info else None
            elif state == 'FAILURE':
                payload['error'] = str(info) if info else 'Unknown error'

            event_data = json.dumps(payload)
            # Only yield if state changed or has progress data
            cache_key = f'{state}:{event_data}'
            if cache_key not in sent_states:
                sent_states.add(cache_key)
                yield f'data: {event_data}\n\n'

            if state in ('SUCCESS', 'FAILURE', 'REVOKED'):
                # Send a final "done" event then stop
                yield f'data: {json.dumps({"task_id": task_id, "status": "done"})}\n\n'
                return

        except Exception as exc:
            logger.warning('SSE poll error for task %s: %s', task_id, exc)
            yield f'data: {json.dumps({"task_id": task_id, "status": "error", "error": str(exc)})}\n\n'
            return

        await asyncio.sleep(POLL_INTERVAL)
        elapsed += POLL_INTERVAL

    # Timeout
    yield f'data: {json.dumps({"task_id": task_id, "status": "timeout"})}\n\n'


@router.get('/job-status')
async def job_status_stream(task_id: str, request: Request) -> StreamingResponse:
    """
    Stream Celery task status as Server-Sent Events.

    Usage: GET /api/v1/stream/job-status?task_id=<celery-task-id>
    """
    async def event_stream() -> AsyncGenerator[str, None]:
        async for event in _task_event_generator(task_id):
            # Stop if client disconnected
            if await request.is_disconnected():
                logger.debug('SSE client disconnected for task %s', task_id)
                return
            yield event

    return StreamingResponse(
        event_stream(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
            'Connection': 'keep-alive',
        },
    )
