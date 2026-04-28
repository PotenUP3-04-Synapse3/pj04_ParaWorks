from __future__ import annotations

from typing import Any

import structlog

from backend.core.config import settings
from backend.parsers.base import ParsedDocument

log = structlog.get_logger(__name__)


def _chunk_paragraphs(parsed: ParsedDocument, chunk_size: int, overlap: int) -> list[dict[str, Any]]:
    """단락 기반 청킹: 단락들을 묶어 chunk_size 토큰/문자 이내로 분할."""
    chunks: list[dict[str, Any]] = []
    current_texts: list[str] = []
    current_meta: list[dict] = []
    current_len = 0

    def flush():
        if current_texts:
            chunks.append({
                'content': '\n'.join(current_texts),
                'page_number': current_meta[0].get('page_number'),
                'paragraph_index': current_meta[0].get('paragraph_index'),
                'metadata': {'heading': current_meta[0].get('heading')},
            })

    for para in parsed.paragraphs:
        text = para.get('text', '').strip()
        if not text:
            continue
        text_len = len(text)
        if current_len + text_len > chunk_size and current_texts:
            flush()
            # overlap: 마지막 일부를 다음 청크에 포함
            keep = []
            keep_len = 0
            for prev in reversed(current_meta):
                keep_len += len(prev.get('text', ''))
                keep.insert(0, prev)
                if keep_len >= overlap:
                    break
            current_texts = [p.get('text', '') for p in keep]
            current_meta = keep
            current_len = sum(len(t) for t in current_texts)

        current_texts.append(text)
        current_meta.append(para)
        current_len += text_len

    flush()
    return chunks


class Chunker:
    def __init__(
        self,
        chunk_size: int = settings.chunk_size,
        overlap: int = settings.chunk_overlap,
    ):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, parsed: ParsedDocument) -> list[dict[str, Any]]:
        if parsed.paragraphs:
            chunks = _chunk_paragraphs(parsed, self.chunk_size, self.overlap)
        else:
            # 단순 슬라이딩 윈도우
            text = parsed.text
            chunks = []
            idx = 0
            para_idx = 0
            while idx < len(text):
                end = min(idx + self.chunk_size, len(text))
                chunks.append({
                    'content': text[idx:end],
                    'page_number': None,
                    'paragraph_index': para_idx,
                    'metadata': {},
                })
                idx += self.chunk_size - self.overlap
                para_idx += 1
        return chunks
