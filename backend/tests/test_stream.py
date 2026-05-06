def test_job_status_stream_returns_sse_event(client) -> None:
    sync = client.post('/api/v1/integrations/slack/sync').json()
    response = client.get(f"/api/v1/stream/job-status?job_id={sync['job_id']}")
    assert response.status_code == 200
    assert 'text/event-stream' in response.headers['content-type']
    assert 'event: progress' in response.text
