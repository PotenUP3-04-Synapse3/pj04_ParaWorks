import pytest

from backend.app.documents.parsers import (
    DocumentParserError,
    ParsedDocument,
    ParsedDocumentChunk,
    ParserRun,
)


def test_parsed_document_requires_source_evidence_for_chunks() -> None:
    with pytest.raises(DocumentParserError, match='source evidence'):
        ParsedDocument(
            source_id='',
            source_url='https://drive.google.com/file/d/file-1/view',
            source_snippet='휴가 신청은 HR 시스템에서 진행합니다.',
            permission_level='restricted',
            mime_type='application/vnd.google-apps.document',
            document_version='42',
            revision_id='rev-42',
            content_signature='drive:file-1:42:rev-42',
            parser_run=ParserRun(
                parser_name='google_drive_text_export',
                parser_status='parsed',
                parser_status_reason=None,
            ),
            chunks=[
                ParsedDocumentChunk(
                    chunk_index=0,
                    text='휴가 신청은 HR 시스템에서 진행합니다.',
                    source_snippet='휴가 신청은 HR 시스템에서 진행합니다.',
                    section_path='휴가 정책',
                )
            ],
        )


def test_parsed_document_enriches_chunks_with_parser_metadata() -> None:
    parsed = ParsedDocument(
        source_id='drive:file-1',
        source_url='https://drive.google.com/file/d/file-1/view',
        source_snippet='휴가 신청은 HR 시스템에서 진행합니다.',
        permission_level='restricted',
        mime_type='application/vnd.google-apps.document',
        document_version='42',
        revision_id='rev-42',
        content_signature='drive:file-1:42:rev-42',
        parser_run=ParserRun(
            parser_name='google_drive_text_export',
            parser_status='parsed',
            parser_status_reason=None,
        ),
        chunks=[
            ParsedDocumentChunk(
                chunk_index=0,
                text='휴가 신청은 HR 시스템에서 진행합니다.',
                source_snippet='휴가 신청은 HR 시스템에서 진행합니다.',
                section_path='휴가 정책',
            )
        ],
    )

    chunk = parsed.chunks[0]
    assert chunk.permission_level == 'restricted'
    assert chunk.metadata['source_id'] == 'drive:file-1'
    assert chunk.metadata['source_url'] == 'https://drive.google.com/file/d/file-1/view'
    assert chunk.metadata['parser_name'] == 'google_drive_text_export'
    assert chunk.metadata['parser_status'] == 'parsed'
    assert chunk.metadata['document_version'] == '42'
    assert chunk.metadata['revision_id'] == 'rev-42'
    assert chunk.metadata['content_signature'] == 'drive:file-1:42:rev-42'
    assert len(chunk.content_hash) == 64
