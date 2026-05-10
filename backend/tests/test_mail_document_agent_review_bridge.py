from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agent_runtime import EvidencePacket, PermissionContext
from backend.app.agents.mail_document_agent import (
    MailDocumentAgent,
    MailDocumentAgentModelResponse,
    create_mail_document_agent_review_items,
)
from backend.app.models import (
    AgentRun,
    Document,
    DocumentChunk,
    DocumentVersion,
    ReviewItem,
    Source,
)


class FakeMailDocumentModel:
    def extract(self, packet: EvidencePacket) -> MailDocumentAgentModelResponse:
        included_types = {message.metadata['source_type'] for message in packet.messages}
        assert packet.source_type == 'mail_document'
        assert included_types == {'gmail', 'drive'}
        assert packet.strictest_permission == 'restricted'
        return MailDocumentAgentModelResponse(
            title='Redis source-of-record decision',
            summary='Gmail and Drive evidence agree on Redis for transient state and PostgreSQL for records.',
            item_type='decision',
            confidence_score=0.9,
            input_tokens=1000,
            output_tokens=180,
        )


def seed_chunk(
    db: Session,
    source_type: str,
    source_id: str,
    permission_level: str,
    metadata: dict | None = None,
) -> None:
    source = Source(
        source_type=source_type,
        source_id=source_id,
        source_url=f'https://{source_type}.mock/{source_id}',
        title=f'{source_type} evidence',
        author='owner@example.com',
        permission_level=permission_level,
        raw_metadata={'ts': '2026-04-30T10:00:00+00:00', 'scenario': 'agent-bridge-test'},
    )
    db.add(source)
    db.flush()

    document = Document(source_id=source.id, title=source.title, current_version='v1')
    db.add(document)
    db.flush()

    version = DocumentVersion(document_id=document.id, version='v1', body=f'{source_type} body')
    db.add(version)
    db.flush()

    db.add(
        DocumentChunk(
            version_id=version.id,
            source_id=source.id,
            chunk_index=0,
            text=f'{source_type} body',
            source_snippet=f'{source_type} body',
            permission_level=permission_level,
            metadata_={'source_url': source.source_url, 'source_type': source_type, **(metadata or {})},
        )
    )
    db.commit()


def test_mail_document_agent_bridge_filters_sources_and_persists_run(db_session: Session) -> None:
    seed_chunk(db_session, 'gmail', 'gmail-agent-test', 'internal')
    seed_chunk(db_session, 'drive', 'drive-agent-test', 'restricted')
    seed_chunk(db_session, 'slack', 'slack-agent-test', 'internal')
    agent = MailDocumentAgent(model=FakeMailDocumentModel())

    created = create_mail_document_agent_review_items(
        db=db_session,
        agent=agent,
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
        source_window='mail-docs:2026-05-01',
    )

    assert len(created) == 1
    agent_run = db_session.scalars(select(AgentRun)).one()
    review_item = db_session.scalars(select(ReviewItem)).one()
    assert agent_run.agent_name == 'mail_document_agent'
    assert agent_run.prompt_version == 'mail-document-history:v1'
    assert agent_run.status == 'complete'
    assert agent_run.source_window == 'mail-docs:2026-05-01'
    assert agent_run.total_tokens == 1180
    assert agent_run.permission_level == 'restricted'
    assert agent_run.metadata_['included_source_types'] == ['drive', 'gmail']
    assert agent_run.metadata_['evidence_summary'] == [
        {
            'rank': 1,
            'source_id': 'gmail-agent-test',
            'source_url': 'https://gmail.mock/gmail-agent-test',
            'source_type': 'gmail',
            'timestamp': '2026-04-30T10:00:00+00:00',
            'author': 'owner@example.com',
            'permission_level': 'internal',
            'importance_score': 0,
            'snippet': 'gmail body',
        },
        {
            'rank': 2,
            'source_id': 'drive-agent-test',
            'source_url': 'https://drive.mock/drive-agent-test',
            'source_type': 'drive',
            'timestamp': '2026-04-30T10:00:00+00:00',
            'author': 'owner@example.com',
            'permission_level': 'restricted',
            'importance_score': 0,
            'snippet': 'drive body',
        },
    ]
    assert review_item.payload['agent_run_id'] == agent_run.id
    assert review_item.payload['agent_name'] == 'mail_document_agent'
    assert review_item.source_links == [
        'https://gmail.mock/gmail-agent-test',
        'https://drive.mock/drive-agent-test',
    ]


def test_mail_document_evidence_packet_preserves_parser_status_metadata(db_session: Session) -> None:
    seed_chunk(
        db_session,
        'drive',
        'drive-pdf-test',
        'restricted',
        metadata={
            'parser_name': 'google_drive_metadata',
            'parser_status': 'metadata_only',
            'parser_status_reason': 'pdf_parser_not_enabled',
            'document_version': '42',
            'revision_id': 'rev-42',
            'content_signature': 'drive:file-1:42:rev-42',
            'content_hash': 'hash-42',
        },
    )

    from backend.app.agents.mail_document_agent import (
        build_mail_document_evidence_packet,
    )

    packet = build_mail_document_evidence_packet(
        db=db_session,
        permission_context=PermissionContext(user_id='demo-admin', role='admin'),
        source_window='mail-docs:2026-05-01',
    )

    message = packet.messages[0]
    assert message.metadata['parser_name'] == 'google_drive_metadata'
    assert message.metadata['parser_status'] == 'metadata_only'
    assert message.metadata['parser_status_reason'] == 'pdf_parser_not_enabled'
    assert message.metadata['document_version'] == '42'
    assert message.metadata['revision_id'] == 'rev-42'
    assert message.metadata['content_signature'] == 'drive:file-1:42:rev-42'
    assert message.metadata['content_hash'] == 'hash-42'
