import pytest

from backend.app.documents.parsers import (
    DocumentParserError,
    ParsedDocument,
    ParsedDocumentChunk,
    ParserRun,
    parser_adapter_decision_for_mime_type,
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


def test_parser_adapter_decision_documents_pdf_and_docx_candidates() -> None:
    pdf = parser_adapter_decision_for_mime_type('application/pdf')
    docx = parser_adapter_decision_for_mime_type(
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    )

    assert pdf.parser_status == 'metadata_only'
    assert pdf.parser_status_reason == 'pdf_parser_not_enabled'
    assert pdf.candidate_package == 'pypdf'
    assert pdf.live_enabled is False
    assert docx.parser_status == 'metadata_only'
    assert docx.parser_status_reason == 'docx_parser_not_enabled'
    assert docx.candidate_package == 'python-docx'
    assert docx.live_enabled is False


def test_parser_adapter_decision_keeps_hwp_and_hwpx_unsupported() -> None:
    for mime_type in [
        'application/x-hwp',
        'application/haansofthwp',
        'application/vnd.hancom.hwpx',
    ]:
        decision = parser_adapter_decision_for_mime_type(mime_type)
        assert decision.parser_status == 'unsupported'
        assert decision.parser_status_reason == 'hwp_parser_not_decided'
        assert decision.candidate_package is None
        assert decision.live_enabled is False
