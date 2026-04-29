"""RAG embeddings — OpenAI text-embedding-3-small, async batch processing."""
from __future__ import annotations

import asyncio
import logging
from typing import List

from openai import AsyncOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

EMBEDDING_MODEL = 'text-embedding-3-small'
EMBEDDING_DIM = 1536
MAX_BATCH_SIZE = 100  # OpenAI limit


async def embed_texts(texts: List[str]) -> List[List[float]]:
    """Embed a list of texts in batches. Returns list of embedding vectors."""
    if not texts:
        return []

    all_embeddings: List[List[float]] = []

    for i in range(0, len(texts), MAX_BATCH_SIZE):
        batch = texts[i : i + MAX_BATCH_SIZE]
        response = await _client.embeddings.create(
            model=EMBEDDING_MODEL,
            input=batch,
        )
        batch_embeddings = [item.embedding for item in response.data]
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


async def embed_query(text: str) -> List[float]:
    """Embed a single query string."""
    result = await embed_texts([text])
    return result[0] if result else []
