from dataclasses import dataclass, field, replace

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import EvidenceMessage, EvidencePacket, PermissionContext
from backend.app.agents.rag_orchestrator_agent.agent import (
    DeterministicRagOrchestratorModel,
    RagAnswer,
    RagOrchestratorAgent,
)
from backend.app.agents.rag_orchestrator_agent.llm import (
    RagLlmProviderError,
    RagLlmSettings,
    build_langchain_rag_orchestrator_model,
)
from backend.app.assistant.tool_logging import AssistantToolLogger
from backend.app.core.config import Settings
from backend.app.core.demo_auth import DemoUser
from backend.app.models import (
    AgentRun,
    DecisionRecord,
    DocumentChunk,
    HistoryEvent,
    Source,
    Todo,
)
from backend.app.permissions.service import can_access_permission
from backend.app.rag.vector_store import VectorDocument, VectorStore


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
    relevance_score: float = 0.0
    matched_terms: list[str] = field(default_factory=list)


def answer_question_with_rag(
    *,
    db: Session,
    user: DemoUser,
    question: str,
    agent: RagOrchestratorAgent | None = None,
    settings: Settings | None = None,
    vector_store: VectorStore | None = None,
    tool_logger: AssistantToolLogger | None = None,
) -> RagAnswer:
    selected_agent = agent or build_default_rag_orchestrator_agent(settings)
    if vector_store is None:
        retrieval_backend = 'keyword'
        if tool_logger is not None:
            tool_logger.log('rag_retrieval', 'start backend=keyword')
        matching_candidates = retrieve_matching_evidence_candidates(db=db, question=question)
        visible_candidates = [
            candidate
            for candidate in matching_candidates
            if can_access_permission(user, candidate.permission_level)
        ]
        hidden_match_count = len(matching_candidates) - len(visible_candidates)
    else:
        retrieval_backend = 'pgvector'
        if tool_logger is not None:
            tool_logger.log('rag_retrieval', 'start backend=pgvector')
        vector_result = vector_store.search(query=question, user=user)
        visible_candidates = candidates_from_vector_matches(vector_result.matches)
        hidden_match_count = vector_result.hidden_match_count
    if tool_logger is not None:
        tool_logger.log(
            'rag_retrieval',
            f'result backend={retrieval_backend} source_count={len(visible_candidates)} hidden_count={hidden_match_count}',
        )
    packet = build_rag_evidence_packet(
        candidates=visible_candidates,
        question=question,
        permission_context=PermissionContext(user_id=user.id, role=user.role),
    )

    if tool_logger is not None:
        tool_logger.log('rag_answer', f'start model={_rag_agent_model_label(selected_agent)} source_count={len(packet.messages)}')
    try:
        answer = selected_agent.answer(
            question=question,
            packet=packet,
            hidden_match_count=hidden_match_count,
        )
    except Exception as exc:
        if tool_logger is not None:
            tool_logger.log('rag_answer', f'error error_class={exc.__class__.__name__}')
        raise
    if tool_logger is not None:
        tool_logger.log('rag_answer', f'result model={answer.cost.model_name} source_count={len(answer.source_links)}')
    agent_run = AgentRun(
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
    db.add(agent_run)
    db.flush()
    answer = replace(answer, agent_run_id=agent_run.id)
    db.commit()
    return answer


def build_default_rag_orchestrator_agent(settings: Settings | None) -> RagOrchestratorAgent:
    if settings is None or settings.paraworks_demo_mode:
        return RagOrchestratorAgent(model=DeterministicRagOrchestratorModel())

    llm_settings = RagLlmSettings(
        enabled=settings.agent_llm_enabled or not settings.paraworks_demo_mode,
        provider_order=tuple(settings.agent_llm_provider_order.split(',')),
        openai_api_key=settings.openai_api_key,
        gemini_api_key=settings.gemini_api_key or settings.google_api_key,
        openai_primary_model=settings.agent_llm_openai_primary_model,
        openai_fallback_model=settings.agent_llm_openai_model,
        gemini_model=settings.agent_llm_gemini_model,
        max_input_chars=settings.agent_llm_max_input_chars,
        max_output_tokens=settings.agent_llm_max_output_tokens,
        temperature=settings.agent_llm_temperature,
        timeout_seconds=settings.agent_llm_timeout_seconds,
    )
    try:
        return RagOrchestratorAgent(
            model=build_langchain_rag_orchestrator_model(llm_settings),
            input_cost_per_1m=settings.agent_llm_input_cost_per_1m_tokens,
            output_cost_per_1m=settings.agent_llm_output_cost_per_1m_tokens,
        )
    except RagLlmProviderError:
        # 진심모드라도 키가 없거나 provider 구성이 깨졌다면 로컬 실행을 멈추지 않는다.
        return RagOrchestratorAgent(model=DeterministicRagOrchestratorModel())


def _rag_agent_model_label(agent: RagOrchestratorAgent) -> str:
    model = getattr(agent, 'model', None)
    providers = getattr(model, 'providers', None)
    if providers:
        return ','.join(str(getattr(provider, 'model_name', 'unknown')) for provider in providers)
    return str(getattr(model, 'model_name', model.__class__.__name__ if model is not None else 'unknown'))


def retrieve_matching_evidence_candidates(*, db: Session, question: str) -> list[RagEvidenceCandidate]:
    candidates = [
        *retrieve_matching_chunk_candidates(db=db, question=question),
        *retrieve_matching_knowledge_candidates(db=db, question=question),
    ]
    return sorted(candidates, key=lambda candidate: candidate.relevance_score, reverse=True)


def vector_documents_from_candidates(candidates: list[RagEvidenceCandidate]) -> list[VectorDocument]:
    return [
        VectorDocument(
            document_id=candidate.source_id,
            text=candidate.text,
            source_url=candidate.source_url,
            source_snippet=candidate.source_snippet,
            permission_level=candidate.permission_level,
            metadata={
                **candidate.metadata,
                'author': candidate.author,
                'timestamp': candidate.timestamp,
            },
        )
        for candidate in candidates
    ]


def candidates_from_vector_matches(matches) -> list[RagEvidenceCandidate]:
    return [
        RagEvidenceCandidate(
            source_id=match.document.document_id,
            source_url=match.document.source_url,
            text=match.document.text,
            source_snippet=match.document.source_snippet,
            author=match.document.metadata.get('author'),
            timestamp=str(match.document.metadata.get('timestamp') or ''),
            permission_level=match.document.permission_level,
            metadata={
                **match.document.metadata,
                'vector_score': match.score,
            },
            relevance_score=match.score,
            matched_terms=list(match.document.metadata.get('matched_terms', [])),
        )
        for match in matches
    ]


def retrieve_matching_chunks(*, db: Session, question: str) -> list[tuple[DocumentChunk, Source]]:
    query_terms = _query_terms(question)
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
    candidates: list[RagEvidenceCandidate] = []
    for chunk, source in retrieve_matching_chunks(db=db, question=question):
        score, matched_terms = score_rag_candidate(question=question, text=chunk.text, title=source.title)
        candidates.append(
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
                    'channel_name': source.raw_metadata.get('channel_name'),
                    'author_name': source.raw_metadata.get('author_name'),
                    'category': chunk.metadata_.get('category'),
                    'topic_tag': chunk.metadata_.get('topic_tag'),
                    'importance': chunk.metadata_.get('importance'),
                    'scenario': source.raw_metadata.get('scenario'),
                },
                relevance_score=score,
                matched_terms=matched_terms,
            )
        )
    return sorted(candidates, key=lambda candidate: candidate.relevance_score, reverse=True)


def retrieve_matching_knowledge_candidates(*, db: Session, question: str) -> list[RagEvidenceCandidate]:
    query_terms = _query_terms(question)
    if not query_terms:
        return []

    candidates: list[RagEvidenceCandidate] = []
    decisions = db.scalars(select(DecisionRecord).where(DecisionRecord.review_status == 'approved')).all()
    for decision in decisions:
        text = f'{decision.title}\n{decision.decision_summary}'
        score, matched_terms = score_rag_candidate(question=question, text=text, title=decision.title)
        if matched_terms:
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
                    relevance_score=score,
                    matched_terms=matched_terms,
                )
            )

    history_events = db.scalars(select(HistoryEvent).where(HistoryEvent.review_status == 'approved')).all()
    for event in history_events:
        text = f'{event.title}\n{event.reason}'
        score, matched_terms = score_rag_candidate(question=question, text=text, title=event.title)
        if matched_terms:
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
                    relevance_score=score,
                    matched_terms=matched_terms,
                )
            )

    todos = db.scalars(select(Todo).where(Todo.review_status == 'approved')).all()
    for todo in todos:
        text = f'{todo.title}\n{todo.priority}\n{todo.priority_reason}'
        score, matched_terms = score_rag_candidate(question=question, text=text, title=todo.title)
        if matched_terms:
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
                    relevance_score=score,
                    matched_terms=matched_terms,
                )
            )

    return sorted(candidates, key=lambda candidate: candidate.relevance_score, reverse=True)


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
    relevance_score: float,
    matched_terms: list[str],
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
        relevance_score=relevance_score,
        matched_terms=matched_terms,
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
            metadata={
                **candidate.metadata,
                'relevance_score': candidate.relevance_score,
                'matched_terms': candidate.matched_terms,
            },
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


def score_rag_candidate(*, question: str, text: str, title: str = '') -> tuple[float, list[str]]:
    query_terms = _query_terms(question)
    if not query_terms:
        return 0.0, []
    searchable = f'{title}\n{text}'.lower()
    matched_terms = [term for term in query_terms if term in searchable]
    if not matched_terms:
        return 0.0, []

    exact_phrase_bonus = 1.0 if question.strip().lower() in searchable else 0.0
    coverage = len(matched_terms) / len(query_terms)
    title_hits = sum(1 for term in matched_terms if term in title.lower())
    title_bonus = min(title_hits * 0.15, 0.45)
    return round(coverage + exact_phrase_bonus + title_bonus, 6), matched_terms


def citation_from_candidate(candidate: RagEvidenceCandidate) -> dict[str, object]:
    return {
        'source_id': candidate.source_id,
        'source_url': candidate.source_url,
        'source_type': candidate.metadata.get('source_type'),
        'permission_level': candidate.permission_level,
        'source_snippet': candidate.source_snippet,
        'relevance_score': candidate.relevance_score,
        'matched_terms': candidate.matched_terms,
    }
