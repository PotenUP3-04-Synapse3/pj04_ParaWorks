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

# 처리 대상 소스 타입 정의
MAIL_DOCUMENT_SOURCE_TYPES = ('gmail', 'gmail_attachment', 'drive', 'calendar')


def create_mail_document_agent_review_items(
    *,
    db: Session,
    agent: MailDocumentAgent,
    permission_context: PermissionContext,
    source_window: str,
    source_ids: list[str] | None = None,
    source_types: tuple[str, ...] = MAIL_DOCUMENT_SOURCE_TYPES,
) -> list[ReviewItem]:
    """
    메일 및 문서 에이전트를 실행하여 DB에 검토 항목(ReviewItem)을 생성합니다.
    1. 증거 패킷 구성
    2. 에이전트 실행
    3. 에이전트 실행 기록(AgentRun) 저장
    4. 추출된 후보들을 검토 항목(ReviewItem)으로 저장
    """
    # 1. DB에서 관련 데이터를 조회하여 증거 패킷(Packet) 구성
    packet = build_mail_document_evidence_packet(
        db=db,
        permission_context=permission_context,
        source_window=source_window,
        source_ids=source_ids,
        source_types=source_types,
    )
    if not packet.messages:
        return []

    # 2. 에이전트 실행
    result = agent.run(packet)
    included_source_types = sorted({
        str(message.metadata.get('source_type'))
        for message in packet.messages
        if message.metadata.get('source_type')
    })
    
    # 3. 에이전트 실행 기록 저장 (비용, 토큰 사용량, 캐시 여부 등)
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
    db.flush() # ID 생성을 위해 flush

    # 4. 추출된 각 후보(Candidate)를 검토 항목으로 변환 및 저장
    review_items: list[ReviewItem] = []
    source_payload = {
        'source_ids': _unique_strings(message.source_id for message in packet.messages),
        'source_types': _unique_strings(
            str(message.metadata.get('source_type') or packet.source_type) for message in packet.messages
        ),
        'source_urls': _unique_strings(message.source_url for message in packet.messages),
        'source_authors': _unique_strings(message.author for message in packet.messages if message.author),
    }
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
                **source_payload,
                **candidate.payload_fields,
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
    source_ids: list[str] | None = None,
    source_types: tuple[str, ...] = MAIL_DOCUMENT_SOURCE_TYPES,
) -> EvidencePacket:
    """
    DB의 DocumentChunk와 Source 테이블을 조인하여 에이전트 입력용 증거 패킷을 생성합니다.
    """
    query = (
        select(DocumentChunk, Source)
        .join(Source, DocumentChunk.source_id == Source.id)
        .where(Source.source_type.in_(source_types))
        .order_by(DocumentChunk.id)
    )
    if source_ids is not None:
        query = query.where(Source.source_id.in_(source_ids))
    rows = db.execute(query).all()

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
                **_source_quality_metadata(chunk),
            },
            source_snippet_override=chunk.source_snippet,
        )
        for chunk, source in rows
    ]

    return EvidencePacket(
        source_type='mail_document',
        source_window=source_window,
        messages=messages,
        permission_context=permission_context,
    )


def build_mail_document_agent_preflight(
    *,
    db: Session,
    permission_context: PermissionContext,
    source_window: str,
    input_cost_per_1m: float = 0.15,
    output_cost_per_1m: float = 0.60,
    estimated_output_tokens: int = 256,
) -> dict[str, object]:
    packet = build_mail_document_evidence_packet(
        db=db,
        permission_context=permission_context,
        source_window=source_window,
    )
    input_tokens = _estimate_tokens(packet)
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
        'estimated_input_tokens': input_tokens,
        'estimated_output_tokens': estimated_output_tokens if packet.messages else 0,
        'estimated_cost_usd': (
            (input_tokens * input_cost_per_1m)
            + ((estimated_output_tokens if packet.messages else 0) * output_cost_per_1m)
        ) / 1_000_000,
    }


def _source_quality_metadata(chunk: DocumentChunk) -> dict[str, object]:
    """문서 파싱 품질 및 메타데이터를 추출합니다."""
    keys = (
        'parser_name',
        'parser_status',
        'parser_status_reason',
        'mime_type',
        'document_version',
        'revision_id',
        'content_signature',
        'content_hash',
        'section_path',
        'page_number',
        'event_context_key',
        'event_status',
        'organizer_email',
        'creator_email',
        'recurring_event_id',
        'attendee_response_statuses',
        'attendee_domains',
        'external_domains',
        'has_external_attendees',
        'duration_minutes',
        'start',
        'end',
        'section_path',
    )
    return {key: chunk.metadata_.get(key) for key in keys if key in chunk.metadata_}


def _estimate_tokens(packet: EvidencePacket) -> int:
    return sum(max(1, len(message.text.strip()) // 4) for message in packet.messages if message.text.strip())


def _unique_strings(values) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result
