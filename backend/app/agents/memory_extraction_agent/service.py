from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import (
    EvidenceMessage,
    EvidencePacket,
    PermissionContext,
    build_evidence_summary,
)
from backend.app.agents.memory_extraction_agent.agent import (
    DecisionRecordAgent,
    DeterministicDecisionRecordModel,
    DeterministicHistoryModel,
    DeterministicTimelineModel,
    DeterministicTodoModel,
    HistoryAgent,
    TimelineAgent,
    TodoAgent,
    ValidationAgent,
    _MemoryExtractionAgent,
)
from backend.app.models import AgentRun, DocumentChunk, ReviewItem, Source

MEMORY_EXTRACTION_SOURCE_TYPES = ('slack', 'gmail', 'drive', 'calendar')
DEFAULT_MEMORY_EXTRACTION_AGENTS = (
    TimelineAgent(model=DeterministicTimelineModel()),
    HistoryAgent(model=DeterministicHistoryModel()),
    DecisionRecordAgent(model=DeterministicDecisionRecordModel()),
    TodoAgent(model=DeterministicTodoModel()),
)
DEFAULT_VALIDATION_AGENT = ValidationAgent()


def build_memory_extraction_evidence_packet(
    *,
    db: Session,
    permission_context: PermissionContext,
    source_window: str,
) -> EvidencePacket:
    rows = db.execute(
        select(DocumentChunk, Source)
        .join(Source, DocumentChunk.source_id == Source.id)
        .where(Source.source_type.in_(MEMORY_EXTRACTION_SOURCE_TYPES))
        .order_by(DocumentChunk.id)
    ).all()
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
                **_source_quality_metadata(chunk),
            },
            source_snippet_override=chunk.source_snippet,
        )
        for chunk, source in rows
    ]
    return EvidencePacket(
        source_type='company_memory',
        source_window=source_window,
        messages=messages,
        permission_context=permission_context,
    )


def build_memory_extraction_agent_preflight(
    *,
    db: Session,
    permission_context: PermissionContext,
    source_window: str,
    estimated_output_tokens_per_agent: int = 128,
    input_cost_per_1m: float = 0.15,
    output_cost_per_1m: float = 0.60,
) -> dict[str, object]:
    packet = build_memory_extraction_evidence_packet(
        db=db,
        permission_context=permission_context,
        source_window=source_window,
    )
    input_tokens = _estimate_tokens(packet)
    output_tokens = estimated_output_tokens_per_agent * len(DEFAULT_MEMORY_EXTRACTION_AGENTS) if packet.messages else 0
    included_source_types = sorted({
        str(message.metadata.get('source_type'))
        for message in packet.messages
        if message.metadata.get('source_type')
    })
    return {
        'action': 'preview_only',
        'reason': 'live_llm_execution_not_enabled_for_this_slice',
        'live_llm_execution': False,
        'source_window': packet.source_window,
        'evidence_message_count': len(packet.messages),
        'included_source_types': included_source_types,
        'strictest_permission': packet.strictest_permission,
        'agent_count': len(DEFAULT_MEMORY_EXTRACTION_AGENTS),
        'estimated_input_tokens': input_tokens,
        'estimated_output_tokens': output_tokens,
        'estimated_cost_usd': ((input_tokens * input_cost_per_1m) + (output_tokens * output_cost_per_1m)) / 1_000_000,
    }


def create_memory_extraction_review_items(
    *,
    db: Session,
    packet: EvidencePacket,
    agents: tuple[_MemoryExtractionAgent, ...] = DEFAULT_MEMORY_EXTRACTION_AGENTS,
    validation_agent: ValidationAgent = DEFAULT_VALIDATION_AGENT,
) -> list[ReviewItem]:
    if not packet.messages:
        return []

    review_items: list[ReviewItem] = []
    for agent in agents:
        result = agent.run(packet)
        accepted_candidates = [
            candidate for candidate in result.candidates if validation_agent.accept(candidate)
        ]
        agent_run = AgentRun(
            agent_name=result.agent_name,
            prompt_version=result.prompt_version,
            status='complete',
            source_window=packet.source_window,
            cache_key=result.cache_key,
            model_name=result.cost.model_name,
            input_tokens=result.cost.token_usage.input_tokens,
            output_tokens=result.cost.token_usage.output_tokens,
            total_tokens=result.cost.token_usage.total_tokens,
            estimated_cost_usd=result.cost.estimated_cost_usd,
            permission_level=packet.strictest_permission,
            metadata_={
                'source_type': packet.source_type,
                'message_count': len(packet.messages),
                'cache_hit': result.cost.cache_hit,
                'validation_status': 'accepted' if accepted_candidates else 'rejected',
                'validation_min_confidence': validation_agent.min_confidence,
                'evidence_summary': build_evidence_summary(packet),
            },
        )
        db.add(agent_run)
        db.flush()

        for candidate in accepted_candidates:
            review_item = ReviewItem(
                status='pending_review',
                item_type=candidate.item_type,
                payload={
                    'title': candidate.title,
                    'summary': candidate.summary,
                    **candidate.payload_fields,
                    'agent_name': result.agent_name,
                    'agent_run_id': agent_run.id,
                    'prompt_version': result.prompt_version,
                    'cache_key': result.cache_key,
                    'estimated_cost_usd': result.cost.estimated_cost_usd,
                    'token_usage': {
                        'input_tokens': result.cost.token_usage.input_tokens,
                        'output_tokens': result.cost.token_usage.output_tokens,
                        'total_tokens': result.cost.token_usage.total_tokens,
                    },
                    'uncertainty_reason': candidate.uncertainty_reason,
                },
                source_links=candidate.source_links,
                source_snippets=candidate.source_snippets,
                confidence_score=candidate.confidence_score,
                permission_level=candidate.permission_level,
            )
            db.add(review_item)
            review_items.append(review_item)

    db.commit()
    for review_item in review_items:
        db.refresh(review_item)
    return review_items


def _source_quality_metadata(chunk: DocumentChunk) -> dict[str, object]:
    keys = (
        'parser_name',
        'parser_status',
        'parser_status_reason',
        'mime_type',
        'section_path',
        'page_number',
        'start',
        'end',
        'event_context_key',
        'event_status',
        'organizer_email',
    )
    return {key: chunk.metadata_.get(key) for key in keys if key in chunk.metadata_}


def _estimate_tokens(packet: EvidencePacket) -> int:
    return sum(max(1, len(message.text.strip()) // 4) for message in packet.messages if message.text.strip())
