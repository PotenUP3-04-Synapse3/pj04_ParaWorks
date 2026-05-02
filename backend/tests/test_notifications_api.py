from backend.app.models import AgentRun, ReviewItem


def test_notifications_api_returns_review_and_agent_run_alerts(client, db_session) -> None:
    db_session.add_all(
        [
            ReviewItem(
                item_type='decision_record',
                payload={'title': 'Redis decision'},
                source_links=['https://slack.mock/redis'],
                source_snippets=['Redis decision source'],
                confidence_score=0.82,
                permission_level='internal',
                status='pending_review',
            ),
            ReviewItem(
                item_type='history_event',
                payload={'title': 'Scope history'},
                source_links=['https://gmail.mock/scope'],
                source_snippets=['Scope source'],
                confidence_score=0.62,
                permission_level='internal',
                status='needs_more_evidence',
            ),
            AgentRun(
                agent_name='slack_agent',
                prompt_version='slack-timeline:v1',
                status='failed',
                source_window='slack:test',
                cache_key='failed-run-cache',
                model_name='fake-model',
                permission_level='internal',
                metadata_={'failure_reason': 'provider timeout'},
            ),
        ]
    )
    db_session.commit()

    response = client.get('/api/v1/notifications')

    assert response.status_code == 200
    payload = response.json()
    assert payload['counts'] == {
        'total': 3,
        'review': 2,
        'agent_runs': 1,
    }
    assert [item['category'] for item in payload['notifications']] == [
        'review',
        'review',
        'agent_run',
    ]
    assert payload['notifications'][0]['action_href'] == '/review'
    assert payload['notifications'][1]['severity'] == 'warning'
    assert payload['notifications'][2]['message'] == 'provider timeout'
