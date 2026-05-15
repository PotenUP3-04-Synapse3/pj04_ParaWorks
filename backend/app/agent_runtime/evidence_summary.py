from backend.app.agent_runtime.contracts import EvidencePacket


def build_evidence_summary(packet: EvidencePacket) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for index, message in enumerate(packet.messages, start=1):
        row = {
            'rank': _int_or_default(message.metadata.get('evidence_rank'), index),
            'source_id': message.source_id,
            'source_url': message.source_url,
            'source_type': message.metadata.get('source_type') or packet.source_type,
            'timestamp': message.timestamp,
            'author': message.author,
            'permission_level': message.permission_level,
            'importance_score': _int_or_default(message.metadata.get('importance_score'), 0),
            'snippet': message.source_snippet,
        }
        for key in (
            'parser_status',
            'section_path',
            'evidence_reason',
            'calendar_id',
            'calendar_summary',
            'event_start',
            'event_end',
            'location',
            'organizer_email',
            'attendee_domains',
            'event_context_key',
        ):
            value = message.metadata.get(key)
            if value:
                row[key] = value
        summary.append(row)
    return summary


def _int_or_default(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return default
