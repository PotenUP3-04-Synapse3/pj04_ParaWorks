from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import EvidenceMessage, EvidencePacket, PermissionContext
from backend.app.agents.rag_orchestrator_agent.agent import (
    DeterministicRagOrchestratorModel,
    RagAnswer,
    RagOrchestratorAgent,
)
from backend.app.core.demo_auth import DemoUser
from backend.app.models import AgentRun, DocumentChunk, Source
from backend.app.permissions.service import can_access_permission


def answer_question_with_rag(
    *,
    db: Session,
    user: DemoUser,
    question: str,
    agent: RagOrchestratorAgent | None = None,
) -> RagAnswer:
    selected_agent = agent or RagOrchestratorAgent(model=DeterministicRagOrchestratorModel())
    matching_rows = retrieve_matching_chunks(db=db, question=question)
    visible_rows = [
        (chunk, source)
        for chunk, source in matching_rows
        if can_access_permission(user, chunk.permission_level)
    ]
    hidden_match_count = len(matching_rows) - len(visible_rows)
    packet = build_rag_evidence_packet(
        rows=visible_rows,
        question=question,
        permission_context=PermissionContext(user_id=user.id, role=user.role),
    )

    answer = selected_agent.answer(
        question=question,
        packet=packet,
        hidden_match_count=hidden_match_count,
    )
    db.add(
        AgentRun(
            agent_name=answer.agent_name,
            prompt_version=answer.prompt_version,
            status='complete',
            source_window=packet.source_window,
            cache_key=answer.cache_key,
            model_name=answer.cost.model_name,
            input_tokens=answer.cost.token_usage.input_tokens,
            output_tokens=answer.cost.token_usage.output_tokens,
            total_tokens=answer.cost.token_usage.total_tokens,
            estimated_cost_usd=answer.cost.estimated_cost_usd,
            permission_level=answer.permission_level,
            metadata_={
                'source_type': packet.source_type,
                'question': question,
                'source_count': len(answer.source_links),
                'hidden_match_count': hidden_match_count,
                'cache_hit': answer.cost.cache_hit,
            },
        )
    )
    db.commit()
    return answer


def retrieve_matching_chunks(*, db: Session, question: str) -> list[tuple[DocumentChunk, Source]]:
    query_terms = [
        term.strip().lower()
        for term in question.replace(',', ' ').replace('.', ' ').split()
        if len(term.strip()) >= 3
    ]
    rows = db.execute(
        select(DocumentChunk, Source)
        .join(Source, DocumentChunk.source_id == Source.id)
        .order_by(DocumentChunk.id)
    ).all()
    if not query_terms:
        return []

    matching_rows: list[tuple[DocumentChunk, Source]] = []
    for chunk, source in rows:
        searchable = f'{chunk.text} {source.title}'.lower()
        if any(term in searchable for term in query_terms):
            matching_rows.append((chunk, source))
    return matching_rows


def build_rag_evidence_packet(
    *,
    rows: list[tuple[DocumentChunk, Source]],
    question: str,
    permission_context: PermissionContext,
) -> EvidencePacket:
    messages = [
        EvidenceMessage(
            source_id=source.source_id,
            source_url=source.source_url,
            text=chunk.text,
            author=source.author,
            timestamp=str(source.raw_metadata.get('ts') or source.created_at.isoformat()),
            permission_level=chunk.permission_level,
            metadata={
                'chunk_id': chunk.id,
                'source_pk': source.id,
                'source_type': source.source_type,
                'scenario': source.raw_metadata.get('scenario'),
            },
        )
        for chunk, source in rows
    ]

    return EvidencePacket(
        source_type='rag',
        source_window=f'ask:{question[:80]}',
        messages=messages,
        permission_context=permission_context,
    )
