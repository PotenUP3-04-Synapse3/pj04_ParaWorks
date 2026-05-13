from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.api.v1 import assistant as assistant_api
from backend.app.models import AgentRun, AssistantMessage
from backend.tests.test_rag_orchestrator_service import seed_chunk


def test_assistant_conversation_api_is_user_scoped(client: TestClient) -> None:
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': 'Viewer Redis 질문'},
        headers={'X-Demo-User': 'viewer'},
    )
    assert create_response.status_code == 200
    conversation_id = create_response.json()['conversation']['id']

    other_user_response = client.get(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        headers={'X-Demo-User': 'hanvv-employee'},
    )

    assert other_user_response.status_code == 404
    assert other_user_response.json()['detail'] == 'assistant conversation not found'


def test_assistant_message_flow_stores_rag_answer_without_cost_fields(
    client: TestClient,
    db_session: Session,
) -> None:
    seed_chunk(
        db_session,
        'gmail',
        'gmail-redis-assistant',
        'Redis should be used for transient job state while PostgreSQL stores durable records.',
        'internal',
    )
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': 'Redis 질문'},
        headers={'X-Demo-User': 'viewer'},
    )
    conversation_id = create_response.json()['conversation']['id']

    turn_response = client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': 'Redis job state'},
        headers={'X-Demo-User': 'viewer'},
    )

    assert turn_response.status_code == 200
    payload = turn_response.json()
    assert payload['user_message']['role'] == 'user'
    assert payload['assistant_message']['role'] == 'assistant'
    assert payload['assistant_message']['source_links'] == ['https://gmail.mock/gmail-redis-assistant']
    assert payload['assistant_message']['hidden_match_count'] == 0
    assert payload['assistant_message']['agent_run_id'] == db_session.query(AgentRun).one().id
    assert 'estimated_cost_usd' not in payload['assistant_message']
    assert 'token_usage' not in payload['assistant_message']
    assert 'cache_key' not in payload['assistant_message']


def test_assistant_email_request_creates_approval_draft_without_rag(
    client: TestClient,
    monkeypatch,
) -> None:
    class FakeEmailActionAgent:
        def decide(self, **kwargs):
            return assistant_api.EmailActionDecision(
                action_type='email_draft',
                to=['partner@example.com'],
                subject='회의 취소 안내',
                body='안녕하세요.\n\n오늘 회의가 취소되었습니다.\n\n감사합니다.',
            )

    def fail_if_rag_runs(**kwargs):
        raise AssertionError('메일 작성 요청은 RAG 근거 확인 없이 액션 초안으로 라우팅되어야 합니다.')

    monkeypatch.setattr(assistant_api, 'build_email_action_agent', lambda settings: FakeEmailActionAgent())
    monkeypatch.setattr(assistant_api, 'answer_question_with_rag', fail_if_rag_runs)
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': '메일 작성'},
        headers={'X-Demo-User': 'viewer'},
    )
    conversation_id = create_response.json()['conversation']['id']

    turn_response = client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': 'partner@example.com에 오늘 회의 취소됐다고 메일 보내줘.'},
        headers={'X-Demo-User': 'viewer'},
    )

    assert turn_response.status_code == 200
    assistant_message = turn_response.json()['assistant_message']
    assert assistant_message['role'] == 'assistant'
    assert '메일 초안을 작성했습니다' in assistant_message['content']
    assert '회의 취소 안내' in assistant_message['content']
    assert assistant_message['citations'] == []
    assert assistant_message['metadata']['action_type'] == 'email_draft'
    assert assistant_message['metadata']['status'] == 'pending_approval'
    assert assistant_message['metadata']['email_draft']['to'] == ['partner@example.com']
    assert assistant_message['metadata']['email_draft']['subject'] == '회의 취소 안내'


def test_assistant_email_agent_uses_conversation_context_without_rag(
    client: TestClient,
    monkeypatch,
) -> None:
    class FakeEmailActionAgent:
        def decide(self, **kwargs):
            if kwargs['latest_message'] != '그 분에게 오늘 회의 취소됐다고 메일 보내줘':
                return assistant_api.EmailActionDecision(action_type='not_email')
            assert kwargs['latest_message'] == '그 분에게 오늘 회의 취소됐다고 메일 보내줘'
            assert 'partner@example.com' in kwargs['conversation_context']
            return assistant_api.EmailActionDecision(
                action_type='email_draft',
                to=['partner@example.com'],
                subject='회의 취소 안내',
                body='안녕하세요.\n\n오늘 회의가 취소되었습니다.\n\n감사합니다.',
            )

    def fail_if_rag_runs(**kwargs):
        raise AssertionError('메일 의도를 sub-agent가 판단하면 RAG로 가지 않아야 합니다.')

    monkeypatch.setattr(assistant_api, 'build_email_action_agent', lambda settings: FakeEmailActionAgent())
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': '메일 맥락'},
        headers={'X-Demo-User': 'viewer'},
    )
    conversation_id = create_response.json()['conversation']['id']
    client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': 'partner@example.com은 협력사 담당자입니다.'},
        headers={'X-Demo-User': 'viewer'},
    )
    monkeypatch.setattr(assistant_api, 'answer_question_with_rag', fail_if_rag_runs)

    turn_response = client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': '그 분에게 오늘 회의 취소됐다고 메일 보내줘'},
        headers={'X-Demo-User': 'viewer'},
    )

    assert turn_response.status_code == 200
    assistant_message = turn_response.json()['assistant_message']
    assert assistant_message['metadata']['action_type'] == 'email_draft'
    assert assistant_message['metadata']['prompt_version'] == assistant_api.EMAIL_ACTION_PROMPT_VERSION
    assert assistant_message['metadata']['email_draft']['to'] == ['partner@example.com']
    assert assistant_message['metadata']['email_draft']['subject'] == '회의 취소 안내'


def test_assistant_email_draft_requires_approval_endpoint_before_send(
    client: TestClient,
    monkeypatch,
) -> None:
    class FakeEmailActionAgent:
        def decide(self, **kwargs):
            return assistant_api.EmailActionDecision(
                action_type='email_draft',
                to=['partner@example.com'],
                subject='회의 취소 안내',
                body='안녕하세요.\n\n오늘 회의가 취소되었습니다.\n\n감사합니다.',
            )

    class FakeGmailDraftSender:
        def __init__(self, **kwargs):
            pass

        def send(self, **kwargs):
            return SimpleNamespace(message_id='gmail-sent-1')

    monkeypatch.setattr(assistant_api, 'build_email_action_agent', lambda settings: FakeEmailActionAgent())
    monkeypatch.setattr(assistant_api, 'GmailDraftSender', FakeGmailDraftSender)
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': '메일 승인'},
        headers={'X-Demo-User': 'viewer'},
    )
    conversation_id = create_response.json()['conversation']['id']
    draft_response = client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': 'partner@example.com에 오늘 회의 취소됐다고 메일 보내줘.'},
        headers={'X-Demo-User': 'viewer'},
    )
    draft_message = draft_response.json()['assistant_message']

    send_response = client.post(
        f"/api/v1/assistant/messages/{draft_message['id']}/email/send",
        headers={'X-Demo-User': 'viewer'},
    )

    assert send_response.status_code == 200
    payload = send_response.json()
    assert payload['status'] == 'sent'
    assert payload['gmail_message_id'] == 'gmail-sent-1'
    assert payload['message']['metadata']['status'] == 'sent'
    assert payload['message']['metadata']['gmail_message_id'] == 'gmail-sent-1'


def test_assistant_lists_persisted_messages(client: TestClient, db_session: Session) -> None:
    seed_chunk(
        db_session,
        'drive',
        'drive-redis-assistant',
        'Redis powers short-lived orchestration state.',
        'internal',
    )
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': 'Persisted conversation'},
        headers={'X-Demo-User': 'viewer'},
    )
    conversation_id = create_response.json()['conversation']['id']
    client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': 'Redis orchestration state'},
        headers={'X-Demo-User': 'viewer'},
    )

    messages_response = client.get(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        headers={'X-Demo-User': 'viewer'},
    )

    assert messages_response.status_code == 200
    messages = messages_response.json()['messages']
    assert [message['role'] for message in messages] == ['user', 'assistant']


def test_assistant_rejects_whitespace_message_without_storing(
    client: TestClient,
    db_session: Session,
) -> None:
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': 'Blank content'},
        headers={'X-Demo-User': 'viewer'},
    )
    conversation_id = create_response.json()['conversation']['id']

    turn_response = client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': '   '},
        headers={'X-Demo-User': 'viewer'},
    )

    assert turn_response.status_code == 422
    assert turn_response.json()['detail'] == 'assistant message content is required'
    assert db_session.query(AssistantMessage).count() == 0


def test_assistant_records_failed_message_when_rag_answer_is_blank(
    client: TestClient,
    monkeypatch,
) -> None:
    def blank_answer(**kwargs):
        return SimpleNamespace(
            answer='   ',
            citations=[],
            source_ids=[],
            source_links=[],
            source_snippets=[],
            permission_level='internal',
            hidden_match_count=0,
            permission_notice=None,
            agent_run_id=987,
            agent_name='rag_orchestrator_agent',
            prompt_version='rag-answer:v1',
            question=kwargs['question'],
        )

    monkeypatch.setattr(assistant_api, 'answer_question_with_rag', blank_answer)
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': 'Blank assistant content'},
        headers={'X-Demo-User': 'viewer'},
    )
    conversation_id = create_response.json()['conversation']['id']

    turn_response = client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': 'Redis job state'},
        headers={'X-Demo-User': 'viewer'},
    )

    assert turn_response.status_code == 502
    assert turn_response.json()['detail'] == 'assistant answer generation failed'

    messages_response = client.get(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        headers={'X-Demo-User': 'viewer'},
    )

    assert messages_response.status_code == 200
    messages = messages_response.json()['messages']
    assert [message['role'] for message in messages] == ['user', 'assistant']
    assert messages[0]['content'] == 'Redis job state'
    failed_message = messages[1]
    assert failed_message['content'] == assistant_api.ASSISTANT_FAILURE_CONTENT
    assert failed_message['citations'] == []
    assert failed_message['source_ids'] == []
    assert failed_message['source_links'] == []
    assert failed_message['source_snippets'] == []
    assert failed_message['agent_run_id'] == 987
    assert failed_message['metadata']['status'] == 'failed'
    assert failed_message['metadata']['failure_reason'] == 'blank_answer'
    assert failed_message['metadata']['failure_class'] == 'ValueError'
    assert 'estimated_cost_usd' not in failed_message
    assert 'token_usage' not in failed_message
    assert 'cache_key' not in failed_message


def test_assistant_records_failed_message_when_rag_answer_fails(
    client: TestClient,
    monkeypatch,
) -> None:
    def failing_answer(**kwargs):
        raise RuntimeError('rag unavailable')

    monkeypatch.setattr(assistant_api, 'answer_question_with_rag', failing_answer)
    create_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': 'RAG failure'},
        headers={'X-Demo-User': 'viewer'},
    )
    conversation_id = create_response.json()['conversation']['id']

    turn_response = client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': 'Redis job state'},
        headers={'X-Demo-User': 'viewer'},
    )

    assert turn_response.status_code == 502
    assert turn_response.json()['detail'] == 'assistant answer generation failed'

    messages_response = client.get(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        headers={'X-Demo-User': 'viewer'},
    )

    assert messages_response.status_code == 200
    messages = messages_response.json()['messages']
    assert [message['role'] for message in messages] == ['user', 'assistant']
    assert messages[0]['content'] == 'Redis job state'
    failed_message = messages[1]
    assert failed_message['content'] == assistant_api.ASSISTANT_FAILURE_CONTENT
    assert failed_message['citations'] == []
    assert failed_message['source_ids'] == []
    assert failed_message['source_links'] == []
    assert failed_message['source_snippets'] == []
    assert failed_message['permission_level'] is None
    assert failed_message['hidden_match_count'] == 0
    assert failed_message['permission_notice'] is None
    assert failed_message['agent_run_id'] is None
    assert failed_message['metadata']['status'] == 'failed'
    assert failed_message['metadata']['failure_reason'] == 'rag_exception'
    assert failed_message['metadata']['failure_class'] == 'RuntimeError'
    assert 'estimated_cost_usd' not in failed_message
    assert 'token_usage' not in failed_message
    assert 'cache_key' not in failed_message


def test_assistant_conversations_list_is_user_scoped(client: TestClient) -> None:
    client.post(
        '/api/v1/assistant/conversations',
        json={'title': 'Viewer conversation'},
        headers={'X-Demo-User': 'viewer'},
    )
    client.post(
        '/api/v1/assistant/conversations',
        json={'title': 'Employee conversation'},
        headers={'X-Demo-User': 'hanvv-employee'},
    )

    list_response = client.get(
        '/api/v1/assistant/conversations',
        headers={'X-Demo-User': 'viewer'},
    )

    assert list_response.status_code == 200
    conversations = list_response.json()['conversations']
    assert [conversation['title'] for conversation in conversations] == ['Viewer conversation']


def test_assistant_create_reuses_existing_empty_new_conversation(client: TestClient) -> None:
    first_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': '새 대화'},
        headers={'X-Demo-User': 'viewer'},
    )
    second_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': '새 대화'},
        headers={'X-Demo-User': 'viewer'},
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json()['conversation']['id'] == first_response.json()['conversation']['id']


def test_assistant_create_makes_new_conversation_after_empty_one_is_used(client: TestClient) -> None:
    first_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': '새 대화'},
        headers={'X-Demo-User': 'viewer'},
    )
    conversation_id = first_response.json()['conversation']['id']
    client.post(
        f'/api/v1/assistant/conversations/{conversation_id}/messages',
        json={'content': 'Redis job state'},
        headers={'X-Demo-User': 'viewer'},
    )

    second_response = client.post(
        '/api/v1/assistant/conversations',
        json={'title': '새 대화'},
        headers={'X-Demo-User': 'viewer'},
    )

    assert second_response.status_code == 200
    assert second_response.json()['conversation']['id'] != conversation_id
