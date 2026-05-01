from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import EvidenceMessage, EvidencePacket, PermissionContext
from backend.app.agents.rag_orchestrator_agent.agent import (
    DeterministicRagOrchestratorModel,
    RagAnswer,
    RagOrchestratorAgent,
)
from backend.app.core.demo_auth import DemoUser
from backend.app.models import AgentRun, DecisionRecord, DocumentChunk, HistoryEvent, Source, Todo
from backend.app.permissions.service import can_access_permission


@dataclass(frozen=True)
class RagEvidenceCandidate:
    source_id: str
    source_url: str
    text: str
    source_snippet: str
    author: str | None
    timestamp: str
    permission_level: str
    metadata: dict


def answer_question_with_rag(
    *,
    db: Session,
    user: DemoUser,
    question: str,
    agent: RagOrchestratorAgent | None = None,
) -> RagAnswer:
    selected_agent = agent or RagOrchestratorAgent(model=DeterministicRagOrchestratorModel())
    matching_candidates = retrieve_matching_evidence_candidates(db=db, question=question)
    visible_candidates = [
        candidate
        for candidate in matching_candidates
        if can_access_permission(user, candidate.permission_level)
    ]
    hidden_match_count = len(matching_candidates) - len(visible_candidates)
    packet = build_rag_evidence_packet(
        candidates=visible_candidates,
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


def retrieve_matching_evidence_candidates(*, db: Session, question: str) -> list[RagEvidenceCandidate]:
    return [
        *retrieve_matching_chunk_candidates(db=db, question=question),
        *retrieve_matching_knowledge_candidates(db=db, question=question),
    ]


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


def retrieve_matching_chunk_candidates(*, db: Session, question: str) -> list[RagEvidenceCandidate]:
    return [
        RagEvidenceCandidate(
            source_id=source.source_id,
            source_url=source.source_url,
            text=chunk.text,
            source_snippet=chunk.source_snippet,
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
        for chunk, source in retrieve_matching_chunks(db=db, question=question)
    ]


def retrieve_matching_knowledge_candidates(*, db: Session, question: str) -> list[RagEvidenceCandidate]:
    query_terms = _query_terms(question)
    if not query_terms:
        return []

    candidates: list[RagEvidenceCandidate] = []
    decisions = db.scalars(select(DecisionRecord).where(DecisionRecord.review_status == 'approved')).all()
    for decision in decisions:
        text = f'{decision.title}\n{decision.decision_summary}'
        if _matches_terms(text, query_terms):
            candidates.append(
                _knowledge_candidate(
                    source_id=f'decision_record:{decision.id}',
                    source_type='decision_record',
                    title=decision.title,
                    text=text,
                    source_links=decision.source_links,
                    source_snippets=decision.source_snippets,
                    permission_level=decision.permission_level,
                    created_at=decision.created_at.isoformat(),
                )
            )

    history_events = db.scalars(select(HistoryEvent).where(HistoryEvent.review_status == 'approved')).all()
    for event in history_events:
        text = f'{event.title}\n{event.reason}'
        if _matches_terms(text, query_terms):
            candidates.append(
                _knowledge_candidate(
                    source_id=f'history_event:{event.id}',
                    source_type='history_event',
                    title=event.title,
                    text=text,
                    source_links=event.source_links,
                    source_snippets=event.source_snippets,
                    permission_level=event.permission_level,
                    created_at=event.created_at.isoformat(),
                )
            )

    todos = db.scalars(select(Todo).where(Todo.review_status == 'approved')).all()
    for todo in todos:
        text = f'{todo.title}\n{todo.priority}\n{todo.priority_reason}'
        if _matches_terms(text, query_terms):
            candidates.append(
                _knowledge_candidate(
                    source_id=f'todo:{todo.id}',
                    source_type='todo',
                    title=todo.title,
                    text=text,
                    source_links=todo.source_links,
                    source_snippets=todo.source_snippets,
                    permission_level=todo.permission_level,
                    created_at=todo.created_at.isoformat(),
                )
            )

    return candidates


def _knowledge_candidate(
    *,
    source_id: str,
    source_type: str,
    title: str,
    text: str,
    source_links: list[str],
    source_snippets: list[str],
    permission_level: str,
    created_at: str,
) -> RagEvidenceCandidate:
    source_url = source_links[0] if source_links else f'knowledge://{source_id}'
    source_snippet = source_snippets[0] if source_snippets else text[:240]
    return RagEvidenceCandidate(
        source_id=source_id,
        source_url=source_url,
        text=text,
        source_snippet=source_snippet,
        author=None,
        timestamp=created_at,
        permission_level=permission_level,
        metadata={
            'source_type': source_type,
            'title': title,
            'knowledge_id': source_id,
        },
    )


def build_rag_evidence_packet(
    *,
    candidates: list[RagEvidenceCandidate],
    question: str,
    permission_context: PermissionContext,
) -> EvidencePacket:
    messages = [
        EvidenceMessage(
            source_id=candidate.source_id,
            source_url=candidate.source_url,
            text=candidate.text,
            author=candidate.author,
            timestamp=candidate.timestamp,
            permission_level=candidate.permission_level,
            metadata=candidate.metadata,
            source_snippet_override=candidate.source_snippet,
        )
        for candidate in candidates
    ]

    return EvidencePacket(
        source_type='rag',
        source_window=f'ask:{question[:80]}',
        messages=messages,
        permission_context=permission_context,
    )


def _query_terms(question: str) -> list[str]:
    return [
        term.strip().lower()
        for term in question.replace(',', ' ').replace('.', ' ').split()
        if len(term.strip()) >= 3
    ]


def _matches_terms(text: str, query_terms: list[str]) -> bool:
    searchable = text.lower()
    return any(term in searchable for term in query_terms)
