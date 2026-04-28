from __future__ import annotations

import structlog

from backend.parsers.base import BaseParser, ParsedDocument
from backend.parsers.hwp_parser import HwpParser
from backend.parsers.office_parser import PdfParser, OfficeParser, TextParser

log = structlog.get_logger(__name__)

_PARSERS: list[BaseParser] = [
    HwpParser(),
    PdfParser(),
    OfficeParser(),
    TextParser(),
]


def parse_document(content: bytes | str, mime_type: str, source_url: str | None = None) -> ParsedDocument:
    for parser in _PARSERS:
        if parser.can_parse(mime_type):
            return parser.parse(content, source_url=source_url)
    log.warning('parser.no_match', mime_type=mime_type)
    text = content if isinstance(content, str) else content.decode('utf-8', errors='replace')
    return ParsedDocument(text=text, metadata={'parser': 'fallback_raw'})


__all__ = ['parse_document', 'ParsedDocument', 'BaseParser']
