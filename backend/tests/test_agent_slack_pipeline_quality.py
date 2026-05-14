from agent_slack import agent_slack as agent_module
from agent_slack.agent_slack import SlackAgentState, classify_work_node


def test_agent_slack_work_filter_skips_low_signal_messages_before_llm(monkeypatch) -> None:
    def fail_if_called(*args, **kwargs):  # noqa: ANN002, ANN003
        raise AssertionError('low-signal messages should not call the LLM work filter')

    monkeypatch.setattr(agent_module, 'ChatOpenAI', fail_if_called)
    state = SlackAgentState(
        channel_id='C123',
        messages=[
            {'ts': '1777600800.000100', 'text': '후...'},
            {'ts': '1777600801.000100', 'text': '부탁드립니다.'},
        ],
        openai_api_key='test-key',
    )

    result = classify_work_node(state)

    assert result['is_work_related'] is False
    assert result['processed_text'] == ''
