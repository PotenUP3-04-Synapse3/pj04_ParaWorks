from __future__ import annotations

"""SSE 스트리밍 — 인덱싱·에이전트 실행 진행률 실시간 전송.

클라이언트는 GET /api/v1/stream/job-status?job_id=<uuid> 로 구독.
이벤트 형식:
  data: {"type": "progress", "pct": 50, "message": "청크 처리 중"}
  data: {"type": "done", "message": "완료"}
  data: {"type": "error", "message": "오류 내용"}
"""

import asyncio
import json
from typing import AsyncGenerator

import structlog
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from backend.core.dependencies import CurrentUserId

log = structlog.get_logger(__name__)
router = APIRouter(prefix='/stream', tags=['stream'])

# 인메모리 job 상태 저장소 (프로덕션에서는 Redis pub/sub 사용)
# job_id → asyncio.Queue of events
_job_queues: dict[str, asyncio.Queue] = {}


def get_or_create_queue(job_id: str) -> asyncio.Queue:
    if job_id not in _job_queues:
        _job_queues[job_id] = asyncio.Queue(maxsize=100)
    return _job_queues[job_id]


async def publish_event(job_id: str, event: dict) -> None:
    """백그라운드 태스크에서 이벤트를 큐에 발행."""
    q = get_or_create_queue(job_id)
    try:
        q.put_nowait(event)
    except asyncio.QueueFull:
        log.warning('stream.queue_full', job_id=job_id)


async def _sse_generator(job_id: str, user_id: str) -> AsyncGenerator[str, None]:
    q = get_or_create_queue(job_id)
    try:
        # 연결 확인 이벤트
        yield f'data: {json.dumps({"type": "connected", "job_id": job_id})}\n\n'

        timeout_count = 0
        max_timeouts = 60  # 60 * 2초 = 2분 타임아웃

        while timeout_count < max_timeouts:
            try:
                event = await asyncio.wait_for(q.get(), timeout=2.0)
                yield f'data: {json.dumps(event, ensure_ascii=False)}\n\n'
                if event.get('type') in ('done', 'error'):
                    break
                timeout_count = 0  # 이벤트 수신 시 타임아웃 리셋
            except asyncio.TimeoutError:
                timeout_count += 1
                # 연결 유지 핑
                yield f': ping\n\n'
    finally:
        # 큐 정리
        _job_queues.pop(job_id, None)


@router.get('/job-status')
async def job_status_stream(
    user_id: CurrentUserId,
    job_id: str = Query(...),
):
    """SSE 엔드포인트 — 클라이언트가 구독하여 진행률을 수신."""
    return StreamingResponse(
        _sse_generator(job_id, user_id),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # nginx 버퍼링 비활성화
        },
    )
