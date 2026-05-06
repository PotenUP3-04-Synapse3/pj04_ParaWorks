from backend.app.agent_runtime.contracts import EvidencePacket


def build_evidence_summary(packet: EvidencePacket) -> list[dict[str, object]]:
    summary: list[dict[str, object]] = []
    for index, message in enumerate(packet.messages, start=1):
        summary.append(
            {
                'rank': _int_or_default(message.metadata.get('evidence_rank'), index),
                'source_id': message.source_id,
                'source_url': message.source_url,
                'source_type': message.metadata.get('source_type') or packet.source_type,
                'timestamp': message.timestamp,
                'author': message.author,
                'permission_level': message.permission_level,
                'importance_score': _int_or_default(message.metadata.get('importance_score'), 0),
                'snippet': message.text[:240],
            }
        )
    return summary


def _int_or_default(value: object, default: int) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return default
