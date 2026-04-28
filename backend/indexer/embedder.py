from __future__ import annotations

from typing import Any

import numpy as np
import structlog

from backend.core.config import settings

log = structlog.get_logger(__name__)


class Embedder:
    """임베딩 백엔드 전환 가능: 'azure_openai' | 'sentence_transformers'."""

    def __init__(self):
        self._backend = settings.embedding_backend
        self._model = None

    def _load(self):
        if self._model is not None:
            return
        if self._backend == 'azure_openai':
            from openai import AzureOpenAI  # type: ignore
            self._model = AzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
            )
        else:
            from sentence_transformers import SentenceTransformer  # type: ignore
            self._model = SentenceTransformer(settings.local_embedding_model)

    def embed(self, texts: list[str]) -> list[list[float]]:
        self._load()
        if not texts:
            return []
        if self._backend == 'azure_openai':
            resp = self._model.embeddings.create(  # type: ignore
                model=settings.azure_openai_deployment_embedding,
                input=texts,
                dimensions=settings.azure_openai_embedding_dimensions,
            )
            return [item.embedding for item in resp.data]
        else:
            vecs = self._model.encode(texts, normalize_embeddings=True)  # type: ignore
            return vecs.tolist()

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]
