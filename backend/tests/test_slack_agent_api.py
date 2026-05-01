from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import ReviewItem


def test_slack_agent_review_endpoint_creates_agent_review_item(client, db_session: Session) -> None:
    sync_response = client.post('/api/v1/integrations/slack/sync')
    assert sync_response.status_code == 200

    response = client.post('/api/v1/integrations/slack/agent-review')

    assert response.status_code == 200
    payload = response.json()
    assert payload == {
        'agent_name': 'slack_agent',
        'status': 'complete',
        'created_review_items': 1,
    }

    agent_item = db_session.scalar(
        select(ReviewItem).where(ReviewItem.payload['agent_name'].as_string() == 'slack_agent')
    )
    assert agent_item is not None
    assert agent_item.status == 'pending_review'
    assert agent_item.payload['prompt_version'] == 'slack-timeline:v1'
    assert agent_item.payload['token_usage']['total_tokens'] > 0
    assert agent_item.payload['estimated_cost_usd'] > 0
    assert agent_item.source_links
    assert agent_item.source_snippets
