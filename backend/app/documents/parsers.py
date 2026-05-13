import hashlib
import json
from dataclasses import dataclass, field
from typing import Protocol


class DocumentParserError(ValueError):
    pass


@dataclass(frozen=True)
class ParserRun:
    parser_name: str
    parser_status: str
    parser_status_reason: str | None


@dataclass(frozen=True)
class ParserAdapterDecision:
    mime_type: str
    parser_status: str
    parser_status_reason: str
    candidate_package: str | None = None
    live_enabled: bool = False


@dataclass
class ParsedDocumentChunk:
    chunk_index: int
    text: str
    source_snippet: str
    page_number: int | None = None
    section_path: str | None = None
    permission_level: str = ''
    content_hash: str = ''
    metadata: dict[str, object] = field(default_factory=dict)


@dataclass
class ParsedDocument:
    source_id: str
    source_url: str
    source_snippet: str
    permission_level: str
    mime_type: str
    document_version: str
    revision_id: str
    content_signature: str
    parser_run: ParserRun
    chunks: list[ParsedDocumentChunk]

    def __post_init__(self) -> None:
        if self.chunks and not (self.source_id and self.source_url and self.source_snippet):
            raise DocumentParserError('Parsed document chunks require source evidence')
        for chunk in self.chunks:
            chunk.permission_level = self.permission_level
            chunk.metadata.update(self._chunk_metadata(chunk))
            chunk.content_hash = _content_hash(
                {
                    'source_id': self.source_id,
                    'source_url': self.source_url,
                    'permission_level': self.permission_level,
                    'mime_type': self.mime_type,
                    'document_version': self.document_version,
                    'revision_id': self.revision_id,
                    'content_signature': self.content_signature,
                    'parser_name': self.parser_run.parser_name,
                    'chunk_index': chunk.chunk_index,
                    'text': chunk.text,
                    'page_number': chunk.page_number,
                    'section_path': chunk.section_path,
                }
            )

    def _chunk_metadata(self, chunk: ParsedDocumentChunk) -> dict[str, object]:
        return {
            'source_id': self.source_id,
            'source_url': self.source_url,
            'permission_level': self.permission_level,
            'mime_type': self.mime_type,
            'document_version': self.document_version,
            'revision_id': self.revision_id,
            'content_signature': self.content_signature,
            'parser_name': self.parser_run.parser_name,
            'parser_status': self.parser_run.parser_status,
            'parser_status_reason': self.parser_run.parser_status_reason,
            'chunk_index': chunk.chunk_index,
            'page_number': chunk.page_number,
            'section_path': chunk.section_path,
        }


class DocumentParser(Protocol):
    parser_name: str

    def parse(self, payload: bytes, *, metadata: dict[str, object]) -> ParsedDocument:
        raise NotImplementedError


def _content_hash(payload: dict[str, object]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()


_PDF_MIME_TYPE = 'application/pdf'
_DOCX_MIME_TYPE = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
_TEXT_PLAIN_MIME_TYPE = 'text/plain'
_MARKDOWN_MIME_TYPE = 'text/markdown'
_HWP_MIME_TYPES = frozenset(
    {
        'application/x-hwp',
        'application/haansofthwp',
        'application/vnd.hancom.hwpx',
    }
)


def parser_adapter_decision_for_mime_type(mime_type: str) -> ParserAdapterDecision:
    normalized = mime_type.strip().lower()
    if normalized == _PDF_MIME_TYPE:
        return ParserAdapterDecision(
            mime_type=normalized,
            parser_status='parsed',
            parser_status_reason='',
            candidate_package='pypdf',
            live_enabled=True,
        )
    if normalized == _DOCX_MIME_TYPE:
        return ParserAdapterDecision(
            mime_type=normalized,
            parser_status='parsed',
            parser_status_reason='',
            candidate_package='python-docx',
            live_enabled=True,
        )
    if normalized in (_TEXT_PLAIN_MIME_TYPE, _MARKDOWN_MIME_TYPE):
        return ParserAdapterDecision(
            mime_type=normalized,
            parser_status='parsed',
            parser_status_reason='',
            candidate_package='built-in',
            live_enabled=True,
        )
    if normalized in _HWP_MIME_TYPES:
        return ParserAdapterDecision(
            mime_type=normalized,
            parser_status='unsupported',
            parser_status_reason='hwp_parser_not_decided',
        )
    return ParserAdapterDecision(
        mime_type=normalized,
        parser_status='metadata_only',
        parser_status_reason='content_export_not_enabled',
    )
