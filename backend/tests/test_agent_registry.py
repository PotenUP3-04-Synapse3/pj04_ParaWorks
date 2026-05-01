from backend.app.agent_runtime import AgentManifest, AgentRegistry


def test_registry_registers_and_resolves_agent_manifest() -> None:
    registry = AgentRegistry()
    manifest = AgentManifest(
        name='slack_agent',
        owner='Developer A',
        input_contract='EvidencePacket',
        output_contract='AgentRunResult',
        prompt_versions=('slack-timeline:v1',),
        supported_permissions=('internal', 'restricted'),
        capabilities=('timeline_extraction', 'history_generation'),
    )

    registry.register(manifest)

    assert registry.get('slack_agent') == manifest
    assert registry.names == ('slack_agent',)


def test_registry_rejects_duplicate_agent_names() -> None:
    registry = AgentRegistry()
    manifest = AgentManifest(
        name='slack_agent',
        owner='Developer A',
        input_contract='EvidencePacket',
        output_contract='AgentRunResult',
        prompt_versions=('slack-timeline:v1',),
        supported_permissions=('internal',),
        capabilities=('timeline_extraction',),
    )

    registry.register(manifest)

    try:
        registry.register(manifest)
    except ValueError as exc:
        assert str(exc) == 'agent already registered: slack_agent'
    else:
        raise AssertionError('duplicate agent name should be rejected')


def test_registry_finds_agents_by_capability() -> None:
    registry = AgentRegistry()
    registry.register(
        AgentManifest(
            name='slack_agent',
            owner='Developer A',
            input_contract='EvidencePacket',
            output_contract='AgentRunResult',
            prompt_versions=('slack-timeline:v1',),
            supported_permissions=('internal', 'restricted'),
            capabilities=('timeline_extraction',),
        )
    )
    registry.register(
        AgentManifest(
            name='rag_orchestrator_agent',
            owner='Developer C',
            input_contract='EvidencePacket',
            output_contract='AgentRunResult',
            prompt_versions=('rag-answer:v1',),
            supported_permissions=('internal', 'restricted'),
            capabilities=('rag_answering',),
        )
    )

    matches = registry.find_by_capability('rag_answering')

    assert [manifest.name for manifest in matches] == ['rag_orchestrator_agent']
