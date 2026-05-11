from datetime import UTC, datetime

from sqlalchemy.orm import Session

from backend.app.connectors.base import SourceEvent
from backend.app.ingestion.service import ingest_events
from backend.app.models import Document, DocumentChunk, DocumentVersion


def drive_event(
    *,
    version: str = '42',
    revision_id: str = 'rev-42',
    chunk_max_chars: int | None = None,
    body: str = '휴가 신청은 HR 시스템에서 진행합니다.\n승인은 팀장이 검토합니다.',
) -> SourceEvent:
    raw_metadata = {
        'mime_type': 'application/vnd.google-apps.document',
        'document_version': version,
        'revision_id': revision_id,
        'content_signature': f'drive:file-1:{version}:{revision_id}',
        'parser_name': 'google_drive_text_export',
        'parser_status': 'parsed',
        'parser_status_reason': None,
        'source_snippet': body.replace('\n', ' ')[:240],
    }
    if chunk_max_chars is not None:
        raw_metadata['chunk_max_chars'] = chunk_max_chars
    return SourceEvent(
        source_type='drive',
        source_id='drive:file-1',
        source_url='https://drive.google.com/file/d/file-1/view',
        title='휴가 정책',
        body=body,
        author='owner@example.com',
        participants=['owner@example.com'],
        timestamp=datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
        permission_level='restricted',
        raw_metadata=raw_metadata,
    )


def test_ingest_drive_parsed_document_preserves_parser_metadata(db_session: Session) -> None:
    event = drive_event()

    ingest_events(db_session, [event])

    document = db_session.query(Document).one()
    version = db_session.query(DocumentVersion).one()
    chunk = db_session.query(DocumentChunk).one()
    assert document.current_version == '42'
    assert version.version == '42'
    assert version.body == event.body
    assert chunk.text == event.body
    assert chunk.source_snippet == '휴가 신청은 HR 시스템에서 진행합니다. 승인은 팀장이 검토합니다.'
    assert chunk.permission_level == 'restricted'
    assert chunk.metadata_['source_id'] == 'drive:file-1'
    assert chunk.metadata_['source_url'] == 'https://drive.google.com/file/d/file-1/view'
    assert chunk.metadata_['source_type'] == 'drive'
    assert chunk.metadata_['permission_level'] == 'restricted'
    assert chunk.metadata_['mime_type'] == 'application/vnd.google-apps.document'
    assert chunk.metadata_['document_version'] == '42'
    assert chunk.metadata_['revision_id'] == 'rev-42'
    assert chunk.metadata_['content_signature'] == 'drive:file-1:42:rev-42'
    assert chunk.metadata_['parser_name'] == 'google_drive_text_export'
    assert chunk.metadata_['parser_status'] == 'parsed'
    assert chunk.metadata_['parser_status_reason'] is None
    assert len(chunk.metadata_['content_hash']) == 64


def test_ingest_drive_parsed_document_splits_long_body_into_stable_chunks(db_session: Session) -> None:
    body = '\n\n'.join(
        [
            'Hiring policy',
            'Alpha team hiring plan keeps contractor review evidence close to the decision record.',
            'Budget policy',
            'Beta team budget policy requires approval evidence before finance updates.',
            'Launch policy',
            'Gamma launch policy keeps customer escalation notes restricted.',
        ]
    )

    ingest_events(db_session, [drive_event(body=body, chunk_max_chars=120)])

    chunks = db_session.query(DocumentChunk).order_by(DocumentChunk.chunk_index).all()
    assert [chunk.chunk_index for chunk in chunks] == [0, 1, 2]
    assert all(len(chunk.text) <= 120 for chunk in chunks)
    assert [chunk.metadata_['section_path'] for chunk in chunks] == [
        'Hiring policy',
        'Budget policy',
        'Launch policy',
    ]
    assert len({chunk.metadata_['content_hash'] for chunk in chunks}) == 3
    assert all(chunk.permission_level == 'restricted' for chunk in chunks)


def test_ingest_skips_same_content_signature_for_existing_document(db_session: Session) -> None:
    event = drive_event()

    ingest_events(db_session, [event])
    ingest_events(db_session, [event])

    assert db_session.query(Document).count() == 1
    assert db_session.query(DocumentVersion).count() == 1
    assert db_session.query(DocumentChunk).count() == 1


def test_ingest_adds_new_version_when_content_signature_changes(db_session: Session) -> None:
    ingest_events(db_session, [drive_event()])
    ingest_events(
        db_session,
        [
            drive_event(
                version='43',
                revision_id='rev-43',
                body='휴가 신청은 HR 시스템에서 진행합니다.\n승인자는 팀장에서 인사팀으로 변경되었습니다.',
            )
        ],
    )

    document = db_session.query(Document).one()
    versions = db_session.query(DocumentVersion).order_by(DocumentVersion.version).all()
    chunks = db_session.query(DocumentChunk).order_by(DocumentChunk.chunk_index, DocumentChunk.id).all()
    assert document.current_version == '43'
    assert [version.version for version in versions] == ['42', '43']
    assert len(chunks) == 2
    assert chunks[0].metadata_['content_signature'] == 'drive:file-1:42:rev-42'
    assert chunks[1].metadata_['content_signature'] == 'drive:file-1:43:rev-43'
    assert chunks[0].metadata_['content_hash'] != chunks[1].metadata_['content_hash']
