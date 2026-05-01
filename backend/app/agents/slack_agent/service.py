from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import EvidenceMessage, EvidencePacket, PermissionContext
from backend.app.agents.slack_agent.agent import SlackAgent
from backend.app.models import DocumentChunk, ReviewItem, Source


def create_slack_agent_review_items(
    *,
    db: Session,
    agent: SlackAgent,
    permission_context: PermissionContext,
    source_window: str,
) -> list[ReviewItem]:
    packet = build_slack_evidence_packet(
        db=db,
        permission_context=permission_context,
        source_window=source_window,
    )
    if not packet.messages:
        return []

    result = agent.run(packet)
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


def build_slack_evidence_packet(
    *,
    db: Session,
    permission_context: PermissionContext,
    source_window: str,
) -> EvidencePacket:
    rows = db.execute(
        select(DocumentChunk, Source)
        .join(Source, DocumentChunk.source_id == Source.id)
        .where(Source.source_type == 'slack')
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
                'channel_id': source.raw_metadata.get('channel_id'),
            },
        )
        for chunk, source in rows
    ]

    return EvidencePacket(
        source_type='slack',
        source_window=source_window,
        messages=messages,
        permission_context=permission_context,
    )
