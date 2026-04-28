from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ParsedDocument:
    """파서 결과 컨테이너."""
    text: str
    pages: list[str] = field(default_factory=list)       # 페이지별 텍스트
    tables: list[list[list[str]]] = field(default_factory=list)  # 표 데이터
    headings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    # RAG 청킹을 위한 단락 인덱스 포함 구조
    paragraphs: list[dict[str, Any]] = field(default_factory=list)
    # [{text, page_number, paragraph_index, heading}]


class BaseParser(ABC):
    @abstractmethod
    def can_parse(self, mime_type: str) -> bool:
        ...

    @abstractmethod
    def parse(self, content: bytes | str, source_url: str | None = None) -> ParsedDocument:
        ...
