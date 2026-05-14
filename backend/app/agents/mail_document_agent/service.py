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
_PERMISSION_RANK = {'public': 0, 'internal': 1, 'restricted': 2}


def create_mail_document_agent_review_items(
    *,
    db: Session,
    agent: MailDocumentAgent,
    permission_context: PermissionContext,
    source_window: str,
    source_ids: list[str] | None = None,
    source_types: tuple[str, ...] = MAIL_DOCUMENT_SOURCE_TYPES,
    max_messages: int | None = None,
    selection_strategy: str = 'chronological',
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
        max_messages=max_messages,
        selection_strategy=selection_strategy,
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
            'source_window': packet.source_window,
            'selection_strategy': selection_strategy,
            'parser_status_counts': _parser_status_counts(packet),
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


def create_mail_document_agent_review_items_for_changed_sources(
    *,
    db: Session,
    agent: MailDocumentAgent,
    permission_context: PermissionContext,
    source_window: str,
    source_ids: list[str],
    source_types: tuple[str, ...] = MAIL_DOCUMENT_SOURCE_TYPES,
) -> list[ReviewItem]:
    """
    동기화에서 변경된 소스를 검토 큐에 반영합니다.

    Google Drive 문서는 파일 단위로, Gmail은 본문과 첨부를 메일 단위로 묶어
    실행합니다. 이렇게 해야 여러 문서가 한 개 후보로 뭉개지지 않고, 첨부만
    바뀐 경우에도 부모 메일 문맥을 함께 보존할 수 있습니다.
    """
    review_items: list[ReviewItem] = []
    for group_source_ids in _changed_source_groups(
        db=db,
        source_ids=source_ids,
        source_types=source_types,
    ):
        review_items.extend(
            create_mail_document_agent_review_items(
                db=db,
                agent=agent,
                permission_context=permission_context,
                source_window=source_window,
                source_ids=group_source_ids,
                source_types=source_types,
                selection_strategy='source_group',
            )
        )
    return review_items


def build_mail_document_evidence_packet(
    *,
    db: Session,
    permission_context: PermissionContext,
    source_window: str,
    source_ids: list[str] | None = None,
    source_types: tuple[str, ...] = MAIL_DOCUMENT_SOURCE_TYPES,
    max_messages: int | None = None,
    selection_strategy: str = 'chronological',
) -> EvidencePacket:
    """
    DB의 DocumentChunk와 Source 테이블을 조인하여 에이전트 입력용 증거 패킷을 생성합니다.
    """
    query = (
        select(DocumentChunk, Source)
        .join(Source, DocumentChunk.source_id == Source.id)
        .where(Source.source_type.in_(source_types))
        .where(DocumentChunk.permission_level.in_(_allowed_permission_levels(permission_context)))
        .where(Source.permission_level.in_(_allowed_permission_levels(permission_context)))
        .order_by(DocumentChunk.id)
    )
    if source_ids is not None:
        query = query.where(Source.source_id.in_(source_ids))
    rows = db.execute(query).all()
    rows = [(chunk, source) for chunk, source in rows]

    if selection_strategy == 'ranked':
        rows = sorted(
            rows,
            key=lambda row: _mail_document_rank_key(row[0], row[1]),
            reverse=True,
        )

    if max_messages is not None:
        rows = rows[:max(max_messages, 0)]

    messages = [
        EvidenceMessage(
            source_id=source.source_id,
            source_url=source.source_url,
            text=chunk.text,
            author=source.author,
            timestamp=str(source.raw_metadata.get('ts') or source.created_at.isoformat()),
            permission_level=_strictest_permission(chunk.permission_level, source.permission_level),
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


def _parser_status_counts(packet: EvidencePacket) -> dict[str, int]:
    counts: dict[str, int] = {}
    for message in packet.messages:
        status = message.metadata.get('parser_status')
        if isinstance(status, str) and status:
            counts[status] = counts.get(status, 0) + 1
    return counts


def _allowed_permission_levels(permission_context: PermissionContext) -> tuple[str, ...]:
    return permission_context.allowed_permission_levels


def _strictest_permission(*levels: str) -> str:
    return max(levels, key=lambda level: _PERMISSION_RANK.get(level, 1))


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


def _mail_document_rank_key(chunk: DocumentChunk, source: Source) -> tuple[int, float, int]:
    return (_mail_document_importance_score(chunk, source), _source_sort_timestamp(source), chunk.id)


def _mail_document_importance_score(chunk: DocumentChunk, source: Source) -> int:
    text = chunk.text.lower()
    score = 0
    if any(keyword in text for keyword in ('decision', 'decided', 'approved', '계약', '결정')):
        score += 50
    if any(keyword in text for keyword in ('todo', 'due', 'deadline', 'owner', '검토', '준비')):
        score += 35
    if source.source_type == 'gmail':
        score += 10
    if source.source_type in {'drive', 'gmail_attachment'}:
        score += 8
    if source.source_type == 'calendar':
        score += 6
    parser_status = chunk.metadata_.get('parser_status')
    if parser_status == 'parsed':
        score += 10
    if parser_status in {'metadata_only', 'unsupported', 'error'}:
        score -= 5
    if 40 <= len(chunk.text) <= 1600:
        score += 5
    return score


def _source_sort_timestamp(source: Source) -> float:
    raw_metadata = source.raw_metadata or {}
    timestamp = raw_metadata.get('ts') or raw_metadata.get('sync_cursor') or raw_metadata.get('modified_time')
    if isinstance(timestamp, (int, float)):
        return float(timestamp)
    if isinstance(timestamp, str):
        try:
            return float(timestamp)
        except ValueError:
            pass
    return source.created_at.timestamp()


def _changed_source_groups(
    *,
    db: Session,
    source_ids: list[str],
    source_types: tuple[str, ...],
) -> list[list[str]]:
    if not source_ids:
        return []

    rows = db.scalars(
        select(Source)
        .where(Source.source_id.in_(source_ids))
        .where(Source.source_type.in_(source_types))
        .order_by(Source.id)
    ).all()

    groups: dict[str, list[str]] = {}
    for source in rows:
        raw_metadata = source.raw_metadata or {}
        if source.source_type == 'gmail_attachment':
            group_key = str(raw_metadata.get('parent_source_id') or source.source_id)
            parent_source_id = raw_metadata.get('parent_source_id')
            if isinstance(parent_source_id, str) and parent_source_id:
                _append_unique(groups.setdefault(group_key, []), parent_source_id)
            _append_unique(groups.setdefault(group_key, []), source.source_id)
            continue

        group_key = source.source_id
        _append_unique(groups.setdefault(group_key, []), source.source_id)

    return list(groups.values())


def _append_unique(values: list[str], value: str) -> None:
    if value not in values:
        values.append(value)


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
