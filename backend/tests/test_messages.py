from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session


def test_list_message_channels(client: TestClient) -> None:
    response = client.get('/api/v1/messages/channels')

    assert response.status_code == 200
    data = response.json()
    assert [channel['id'] for channel in data['channels']] == [
        'announcements',
        'project-alpha',
        'review-queue',
    ]
    assert data['channels'][0]['name'] == '전체공지'


def test_list_channel_messages(client: TestClient) -> None:
    response = client.get('/api/v1/messages/channels/project-alpha/messages')

    assert response.status_code == 200
    data = response.json()
    assert data['channel']['id'] == 'project-alpha'
    assert len(data['messages']) >= 2
    assert data['messages'][0]['author_name'] == '김민준'


def test_post_channel_message_appends_to_channel(client: TestClient) -> None:
    response = client.post(
        '/api/v1/messages/channels/project-alpha/messages',
        json={'body': 'Redis 작업 상태 공유 감사합니다. 오늘 오후 검토하겠습니다.'},
    )

    assert response.status_code == 200
    created = response.json()
    assert created['body'] == 'Redis 작업 상태 공유 감사합니다. 오늘 오후 검토하겠습니다.'
    assert created['author_name'] == '관리자'

    messages_response = client.get('/api/v1/messages/channels/project-alpha/messages')
    messages = messages_response.json()['messages']
    assert messages[-1]['id'] == created['id']


def test_post_channel_message_persists_in_database(
    client: TestClient,
    db_session: Session,
) -> None:
    response = client.post(
        '/api/v1/messages/channels/review-queue/messages',
        json={'body': 'DB에 남는 메시지인지 확인합니다.'},
    )

    assert response.status_code == 200
    created = response.json()

    stored = db_session.execute(
        text('select body, channel_id from messages where id = :id'),
        {'id': created['id']},
    ).one()
    assert stored.body == 'DB에 남는 메시지인지 확인합니다.'
    assert stored.channel_id == 'review-queue'


def test_unknown_channel_returns_404(client: TestClient) -> None:
    response = client.get('/api/v1/messages/channels/missing/messages')

    assert response.status_code == 404
    assert response.json()['detail'] == 'message channel not found'
