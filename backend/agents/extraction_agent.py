from __future__ import annotations

"""추출 에이전트 — 문서/메시지에서 DecisionRecord/KnowledgeAsset을 자동 추출.

HumanInTheLoopMiddleware로 중요 결정 영속화 전 관리자 승인 처리.
ToolStrategy(DecisionRecordCreate) 구조화 출력.
"""

import json
import uuid
from typing import Any

import structlog
from langchain.agents import create_agent, AgentState  # type: ignore
from langchain.agents.middleware import HumanInTheLoopMiddleware  # type: ignore
from langchain.agents.structured_output import ToolStrategy  # type: ignore
from langchain.tools import tool  # type: ignore
from langgraph.types import Command  # type: ignore

from backend.core.config import settings
from backend.schemas.decision import DecisionRecordCreate
from backend.schemas.knowledge import KnowledgeAssetCreate
from backend.agents.middleware import (
    ToolCallLoggingMiddleware,
    model_retry_middleware,
    ContentModerationMiddleware,
)

log = structlog.get_logger(__name__)


@tool
async def save_decision_record(payload: str) -> str:
    """검증된 DecisionRecord JSON을 DB에 저장합니다. HITL 승인 후 호출됩니다."""
    from backend.core.database import AsyncSessionLocal
    from backend.models.decision_record import DecisionRecord

    data = json.loads(payload)
    record = DecisionRecord(id=str(uuid.uuid4()), **data)
    async with AsyncSessionLocal() as session:
        session.add(record)
        await session.commit()
        await session.refresh(record)
    return json.dumps({'id': record.id, 'status': 'saved'})


@tool
async def save_knowledge_asset(payload: str) -> str:
    """KnowledgeAsset JSON을 DB에 저장합니다."""
    from backend.core.database import AsyncSessionLocal
    from backend.models.knowledge_asset import KnowledgeAsset

    data = json.loads(payload)
    asset = KnowledgeAsset(id=str(uuid.uuid4()), **data)
    async with AsyncSessionLocal() as session:
        session.add(asset)
        await session.commit()
        await session.refresh(asset)
    return json.dumps({'id': asset.id, 'status': 'saved'})


_TOOLS = [save_decision_record, save_knowledge_asset]

_SYSTEM_PROMPT = """\
당신은 조직 문서 분석 AI입니다. 주어진 텍스트에서 다음을 추출하세요:
1. 의사결정 레코드 (DecisionRecord): 언제, 누가, 무엇을 결정했는지, 이유는 무엇인지
2. 지식 자산 (KnowledgeAsset): 암묵지, 노하우, 반복되는 패턴

중요 의사결정 저장 시 HITL 승인이 필요합니다.
모든 추출 결과는 구조화된 JSON 형식으로 반환하세요.
"""


def build_extraction_agent(checkpointer: Any | None = None):
    """추출 에이전트 인스턴스 빌드."""
    hitl_mw = HumanInTheLoopMiddleware(
        interrupt_on={'save_decision_record': True},
    )
    agent = create_agent(
        model=f"azure:{settings.azure_openai_deployment_chat}",
        tools=_TOOLS,
        response_format=ToolStrategy(DecisionRecordCreate),
        middleware=[
            ToolCallLoggingMiddleware(),
            model_retry_middleware,
            ContentModerationMiddleware(),
            hitl_mw,
        ],
        checkpointer=checkpointer,
        system_prompt=_SYSTEM_PROMPT,
    )
    return agent


async def extract_from_text(
    text: str,
    organization_id: str,
    user_id: str,
    thread_id: str | None = None,
    checkpointer: Any | None = None,
) -> dict[str, Any]:
    """텍스트에서 의사결정/지식자산 추출. HITL 인터럽트 시 interrupt 상태 반환."""
    agent = build_extraction_agent(checkpointer=checkpointer)
    tid = thread_id or str(uuid.uuid4())
    config = {'configurable': {'thread_id': tid}}

    initial_state: AgentState = {
        'messages': [{'role': 'user', 'content': f'다음 텍스트를 분석하여 추출하세요:\n\n{text}'}],
        'org_id': organization_id,
        'user_id': user_id,
    }
    result = await agent.ainvoke(initial_state, config=config, version='v2')

    if result.interrupts:
        return {
            'status': 'pending_approval',
            'thread_id': tid,
            'interrupts': [
                {'tool': i.tool_name, 'payload': i.tool_call_args}
                for i in result.interrupts
            ],
        }
    return {'status': 'completed', 'thread_id': tid}


async def resume_extraction(
    thread_id: str,
    decision: str,  # 'approve' | 'reject'
    checkpointer: Any,
) -> dict[str, Any]:
    """HITL 결과를 이어 받아 에이전트를 재개."""
    agent = build_extraction_agent(checkpointer=checkpointer)
    config = {'configurable': {'thread_id': thread_id}}
    resume_cmd = Command(resume={'decisions': [{'type': decision}]})
    result = await agent.ainvoke(resume_cmd, config=config, version='v2')
    return {'status': 'completed', 'thread_id': thread_id}
