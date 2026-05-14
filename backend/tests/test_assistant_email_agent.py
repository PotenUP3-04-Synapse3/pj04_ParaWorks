from backend.app.assistant.email_agent import (
    EmailIntentDecision,
    LangChainEmailDraftComposerModel,
    LangChainEmailIntentGateModel,
)


class FakeChatModel:
    def __init__(self, content: str) -> None:
        self.content = content
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        return self.content


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
