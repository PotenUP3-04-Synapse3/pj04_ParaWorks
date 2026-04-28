from __future__ import annotations

"""인수인계 에이전트 — HandoverPacket 자동 생성.
ProviderStrategy(HandoverPacket, strict=True) 구조화 출력.
"""

import json
import uuid
from typing import Any

import structlog
from langchain.agents import create_agent, AgentState  # type: ignore
from langchain.agents.structured_output import ProviderStrategy  # type: ignore
from langchain.tools import tool  # type: ignore

from backend.core.config import settings
from backend.schemas.knowledge import HandoverPacketCreate
from backend.agents.middleware import (
    ToolCallLoggingMiddleware,
    model_retry_middleware,
    ContentModerationMiddleware,
)

log = structlog.get_logger(__name__)


@tool
async def get_user_decisions(user_id: str, org_id: str, limit: int = 20) -> str:
    """특정 사용자가 참여한 의사결정 레코드를 가져옵니다."""
    from backend.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT id, title, decision_summary, decided_at "
                "FROM decision_records "
                "WHERE organization_id = :org_id "
                "  AND :uid = ANY(participants) "
                "ORDER BY decided_at DESC LIMIT :lim"
            ),
            {'org_id': org_id, 'uid': user_id, 'lim': limit},
        )
        rows = [dict(r._mapping) for r in result.fetchall()]
    return json.dumps(rows, ensure_ascii=False, default=str)


@tool
async def get_user_knowledge_assets(user_id: str, org_id: str, limit: int = 20) -> str:
    """사용자가 작성한 지식 자산을 가져옵니다."""
    from backend.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT id, title, asset_type, summary "
                "FROM knowledge_assets "
                "WHERE organization_id = :org_id "
                "  AND created_by = :uid "
                "ORDER BY updated_at DESC LIMIT :lim"
            ),
            {'org_id': org_id, 'uid': user_id, 'lim': limit},
        )
        rows = [dict(r._mapping) for r in result.fetchall()]
    return json.dumps(rows, ensure_ascii=False, default=str)


@tool
async def get_ongoing_projects(user_id: str, org_id: str) -> str:
    """사용자가 관여한 진행 중인 프로젝트/문서를 가져옵니다."""
    from backend.core.database import AsyncSessionLocal
    from sqlalchemy import text
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text(
                "SELECT dc.id, dc.title, dc.source_type, dv.created_at "
                "FROM document_collections dc "
                "JOIN document_versions dv ON dv.collection_id = dc.id "
                "WHERE dc.organization_id = :org_id "
                "  AND dc.metadata->>'owner_id' = :uid "
                "ORDER BY dv.created_at DESC LIMIT 10"
            ),
            {'org_id': org_id, 'uid': user_id},
        )
        rows = [dict(r._mapping) for r in result.fetchall()]
    return json.dumps(rows, ensure_ascii=False, default=str)


_TOOLS = [get_user_decisions, get_user_knowledge_assets, get_ongoing_projects]

_SYSTEM_PROMPT = """\
당신은 인수인계 패키지 생성 AI입니다.
떠나는 직원의 업무를 분석하여 다음 직원이 빠르게 파악할 수 있는 인수인계 문서를 생성하세요.

포함 항목:
1. 진행 중인 프로젝트 목록 및 현황
2. 참여한 주요 의사결정 및 배경
3. 축적된 지식 자산 (노하우, 주의사항)
4. 예상 리스크 및 권고사항
5. 담당 외부 연락처 및 접근 권한 목록

HandoverPacket 형식으로 반환하세요.
"""


def build_handover_agent(checkpointer: Any | None = None):
    """인수인계 에이전트 빌드."""
    agent = create_agent(
        model=f"azure:{settings.azure_openai_deployment_chat}",
        tools=_TOOLS,
        response_format=ProviderStrategy(HandoverPacketCreate, strict=True),
        middleware=[
            ToolCallLoggingMiddleware(),
            model_retry_middleware,
            ContentModerationMiddleware(),
        ],
        checkpointer=checkpointer,
        system_prompt=_SYSTEM_PROMPT,
    )
    return agent


async def generate_handover_packet(
    user_id: str,
    organization_id: str,
    additional_context: str = '',
    thread_id: str | None = None,
) -> HandoverPacketCreate:
    """사용자 인수인계 패키지를 생성하여 반환."""
    agent = build_handover_agent()
    tid = thread_id or str(uuid.uuid4())
    config = {'configurable': {'thread_id': tid}}

    prompt = f"user_id={user_id}, org_id={organization_id} 사용자의 인수인계 패키지를 생성하세요."
    if additional_context:
        prompt += f"\n\n추가 맥락:\n{additional_context}"

    initial_state: AgentState = {
        'messages': [{'role': 'user', 'content': prompt}],
        'org_id': organization_id,
        'user_id': user_id,
    }
    result = await agent.ainvoke(initial_state, config=config, version='v2')
    return result.structured_output
