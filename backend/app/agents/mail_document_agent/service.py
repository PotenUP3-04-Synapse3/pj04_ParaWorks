from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import (
    EvidenceMessage,
    EvidencePacket,
    PermissionContext,
    build_evidence_summary,
)
from backend.app.agents.mail_document_agent.agent import MailDocumentAgent
from backend.app.models import AgentRun, DocumentChunk, ReviewItem, Source

MAIL_DOCUMENT_SOURCE_TYPES = ('gmail', 'drive')


def create_mail_document_agent_review_items(
    *,
    db: Session,
    agent: MailDocumentAgent,
    permission_context: PermissionContext,
    source_window: str,
) -> list[ReviewItem]:
    packet = build_mail_document_evidence_packet(
        db=db,
        permission_context=permission_context,
        source_window=source_window,
    )
    if not packet.messages:
        return []

    result = agent.run(packet)
    included_source_types = sorted({
        str(message.metadata.get('source_type'))
        for message in packet.messages
        if message.metadata.get('source_type')
    })
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
                'included_source_types': included_source_types,
                'message_count': len(packet.messages),
                'cache_hit': result.cost.cache_hit,
                'evidence_summary': build_evidence_summary(packet),
            },
        )
    db.add(agent_run)
    db.flush()

    review_items: list[ReviewItem] = []
    for candidate in result.candidates:
        candidate.validate_evidence()
        review_item = ReviewItem(
            status='pending_review',
            item_type=candidate.item_type,
            payload={
                'title': candidate.title,
                'summary': candidate.summary,
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


def build_mail_document_evidence_packet(
    *,
    db: Session,
    permission_context: PermissionContext,
    source_window: str,
) -> EvidencePacket:
    rows = db.execute(
        select(DocumentChunk, Source)
        .join(Source, DocumentChunk.source_id == Source.id)
        .where(Source.source_type.in_(MAIL_DOCUMENT_SOURCE_TYPES))
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
                'scenario': source.raw_metadata.get('scenario'),
            },
        )
        for chunk, source in rows
    ]

    return EvidencePacket(
        source_type='mail_document',
        source_window=source_window,
        messages=messages,
        permission_context=permission_context,
    )
