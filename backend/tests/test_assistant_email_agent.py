import json
import sys
from types import SimpleNamespace

from backend.app.assistant.email_agent import (
    EmailIntentDecision,
    LangChainEmailDraftComposerModel,
    LangChainEmailIntentGateModel,
    build_email_draft_composer,
    build_email_intent_gate,
    render_email_action_context,
    render_email_draft_prompt,
    render_recent_assistant_context_for_email,
)
from backend.app.core.config import Settings


class FakeChatModel:
    def __init__(self, content: str) -> None:
        self.content = content
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return self.content


def test_email_draft_composer_defaults_to_stronger_model_than_intent_gate() -> None:
    settings = Settings()

    assert settings.assistant_email_agent_model == 'gpt-4.1-nano'
    assert settings.assistant_email_draft_agent_model == 'gpt-5.4-mini'


def test_email_draft_composer_builder_uses_dedicated_draft_model(monkeypatch) -> None:
    class CapturingChatOpenAI:
        instances = []

        def __init__(self, **kwargs) -> None:
            self.kwargs = kwargs
            self.__class__.instances.append(self)

    monkeypatch.setitem(sys.modules, 'langchain_openai', SimpleNamespace(ChatOpenAI=CapturingChatOpenAI))
    settings = Settings(
        paraworks_demo_mode=False,
        openai_api_key='test-key',
        assistant_email_agent_model='gpt-4.1-nano',
        assistant_email_draft_agent_model='gpt-5.4-mini',
    )

    build_email_intent_gate(settings)
    build_email_draft_composer(settings)

    assert CapturingChatOpenAI.instances[0].kwargs['model'] == 'gpt-4.1-nano'
    assert CapturingChatOpenAI.instances[1].kwargs['model'] == 'gpt-5.4-mini'


def test_email_intent_gate_prompt_only_classifies_email_intent() -> None:
    chat_model = FakeChatModel(
        '{"email_intent": false, "intent_type": "none", "confidence_score": 0.9}'
    )
    model = LangChainEmailIntentGateModel(
        chat_model=chat_model,
        model_name='gpt-4.1-nano',
        max_input_chars=1200,
    )

    decision = model.decide(
        conversation_context='[]',
        latest_message='Redis job state?',
    )

    system_prompt = chat_model.messages[0][1]
    user_prompt = chat_model.messages[1][1]
    assert decision.email_intent is False
    assert 'only job is to decide whether the latest user message requests an email action' in system_prompt
    assert 'Do not write the email body' in system_prompt
    assert 'company-memory RAG' not in system_prompt
    assert 'brief general reply' not in system_prompt
    assert 'email_intent' in user_prompt


def test_email_draft_composer_receives_rag_context_when_required() -> None:
    chat_model = FakeChatModel(
        
            '{"action_type": "email_draft", "to": ["lead@example.com"], '
            '"subject": "Project Alpha launch summary", '
            '"body": "Project Alpha launch is Friday.", "confidence_score": 0.94}'
        
    )
    model = LangChainEmailDraftComposerModel(
        chat_model=chat_model,
        model_name='gpt-4.1-nano',
        max_input_chars=1200,
    )

    decision = model.compose(
        conversation_context='[]',
        latest_message='Email the launch date to lead@example.com.',
        intent=EmailIntentDecision(
            email_intent=True,
            intent_type='send',
            requires_rag_result=True,
        ),
        rag_context='Project Alpha launch is Friday.',
    )

    system_prompt = chat_model.messages[0][1]
    user_prompt = chat_model.messages[1][1]
    assert decision.action_type == 'email_draft'
    assert decision.to == ['lead@example.com']
    assert 'Create a concise Korean business email draft' in system_prompt
    assert 'Never send email directly' in system_prompt
    assert 'Project Alpha launch is Friday.' in user_prompt


def test_email_context_preserves_complete_recent_messages_within_budget() -> None:
    messages = [
        SimpleNamespace(role='assistant', content='older answer ' * 80),
        SimpleNamespace(role='user', content='최근 결정된 사항만 요약해서 종우님한테 이메일 보내줘.'),
        SimpleNamespace(role='assistant', content='최근 결정사항: NDA 준비, 보안 교육 자료 준비, 5/18 온보딩 시작.'),
        SimpleNamespace(role='user', content='kjw4work@gmail.com'),
    ]

    rendered = render_email_action_context(messages=messages, max_chars=180)
    rows = json.loads(rendered)

    assert rows[-1]['content'] == 'kjw4work@gmail.com'
    assert rows[-2]['content'] == '최근 결정사항: NDA 준비, 보안 교육 자료 준비, 5/18 온보딩 시작.'
    assert all('role' in row and 'content' in row for row in rows)


def test_recent_assistant_context_supplies_email_body_material() -> None:
    messages = [
        SimpleNamespace(role='user', content='최근 결정된 사항만 요약해줘'),
        SimpleNamespace(role='assistant', content='최근 결정사항: NDA 준비, 보안 교육 자료 준비, 5/18 온보딩 시작.'),
        SimpleNamespace(role='user', content='kjw4work@gmail.com'),
    ]

    context = render_recent_assistant_context_for_email(messages=messages, max_chars=500)

    assert '최근 결정사항' in context
    assert '5/18 온보딩 시작' in context


def test_email_draft_prompt_allows_recipient_only_continuation_with_prior_context() -> None:
    prompt = render_email_draft_prompt(
        conversation_context='[{"role":"assistant","content":"최근 결정사항: NDA 준비, 보안 교육 자료 준비"}]',
        latest_message='kjw4work@gmail.com',
        intent=EmailIntentDecision(email_intent=True, intent_type='send'),
        rag_context='Previous assistant answer:\n최근 결정사항: NDA 준비, 보안 교육 자료 준비',
        max_input_chars=1000,
    )

    assert 'If the latest message only provides a recipient or address' in prompt
    assert 'Previous assistant answer' in prompt
