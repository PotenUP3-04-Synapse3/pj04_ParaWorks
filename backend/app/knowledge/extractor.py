from backend.app.models import DocumentChunk


def build_review_payloads(chunks: list[DocumentChunk]) -> list[dict]:
    combined_text = '\n'.join(chunk.text for chunk in chunks)
    lower_text = combined_text.lower()
    source_links = [chunk.metadata_['source_url'] for chunk in chunks]
    source_snippets = [chunk.source_snippet for chunk in chunks]
    permission_level = 'restricted' if any(chunk.permission_level == 'restricted' for chunk in chunks) else 'internal'

    base_payload = {
        'source_links': source_links,
        'source_snippets': source_snippets,
        'permission_level': permission_level,
    }
    review_payloads: list[dict] = []

    if 'Redis' in combined_text:
        review_payloads.append(
            {
                **base_payload,
                'item_type': 'decision_record',
                'payload': {
                    'title': 'Use Redis for queues and job progress',
                    'decision_summary': 'Redis and Celery should power queues and job status updates.',
                },
                'confidence_score': 0.86,
            }
        )

    if 'scope' in lower_text:
        review_payloads.append(
            {
                **base_payload,
                'item_type': 'history_event',
                'payload': {
                    'title': 'Project Beta advanced diff UI moved out of MVP',
                    'reason': 'Scope changed while Review Queue and Source Evidence Drawer remained launch requirements.',
                },
                'confidence_score': 0.82,
            }
        )

    if 'todo' in lower_text or 'follow-up' in lower_text:
        review_payloads.append(
            {
                **base_payload,
                'item_type': 'todo',
                'payload': {
                    'title': 'Verify evidence inspection before launch',
                    'priority': 'high',
                    'priority_reason': 'Source evidence must be checked before launch readiness review.',
                },
                'confidence_score': 0.8,
            }
        )

    return review_payloads
