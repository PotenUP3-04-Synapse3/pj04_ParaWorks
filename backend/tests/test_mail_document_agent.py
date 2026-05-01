from backend.app.agent_runtime import EvidenceMessage, EvidencePacket, PermissionContext
from backend.app.agents.mail_document_agent import (
    MAIL_DOCUMENT_AGENT_MANIFEST,
    MAIL_DOCUMENT_AGENT_PROMPT_VERSION,
    MailDocumentAgent,
    MailDocumentAgentModelResponse,
)


class FakeMailDocumentModel:
    def extract(self, packet: EvidencePacket) -> MailDocumentAgentModelResponse:
        assert packet.source_type == 'mail_document'
        return MailDocumentAgentModelResponse(
            title='Redis architecture decision',
            summary='Gmail and Drive evidence confirm Redis is used for transient job state.',
            item_type='decision',
            confidence_score=0.86,
            input_tokens=900,
            output_tokens=160,
        )


def test_mail_document_agent_manifest_declares_shared_contracts() -> None:
    assert MAIL_DOCUMENT_AGENT_MANIFEST.name == 'mail_document_agent'
    assert MAIL_DOCUMENT_AGENT_MANIFEST.input_contract == 'EvidencePacket'
    assert MAIL_DOCUMENT_AGENT_MANIFEST.output_contract == 'AgentRunResult'
    assert MAIL_DOCUMENT_AGENT_PROMPT_VERSION in MAIL_DOCUMENT_AGENT_MANIFEST.prompt_versions
    assert 'history_generation' in MAIL_DOCUMENT_AGENT_MANIFEST.capabilities


def test_mail_document_agent_creates_evidence_backed_candidate() -> None:
    packet = EvidencePacket(
        source_type='mail_document',
        source_window='mail-docs:all',
        messages=[
            EvidenceMessage(
                source_id='gmail-1',
                source_url='https://gmail.mock/project-alpha/redis-summary',
                text='Redis should be used for transient job state.',
                author='noah@example.com',
                timestamp='2026-04-30T10:15:00+00:00',
                permission_level='internal',
                metadata={'source_type': 'gmail'},
            ),
            EvidenceMessage(
                source_id='drive-1',
                source_url='https://drive.mock/project-alpha/architecture-note',
                text='Architecture note: Redis-backed updates replace polling.',
                author='lee@example.com',
                timestamp='2026-04-30T11:00:00+00:00',
                permission_level='internal',
                metadata={'source_type': 'drive'},
            ),
        ],
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
    )
    result = MailDocumentAgent(model=FakeMailDocumentModel()).run(packet)

    assert result.agent_name == 'mail_document_agent'
    assert result.prompt_version == 'mail-document-history:v1'
    assert result.candidates[0].source_links == [
        'https://gmail.mock/project-alpha/redis-summary',
        'https://drive.mock/project-alpha/architecture-note',
    ]
    assert result.cost.token_usage.total_tokens == 1060
    assert result.cost.estimated_cost_usd > 0
    assert result.cache_key
