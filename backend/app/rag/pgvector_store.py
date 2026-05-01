from dataclasses import dataclass
import json
import re
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser
from backend.app.rag.vector_store import VectorDocument, VectorMatch, VectorSearchResult


@dataclass(frozen=True)
class PgVectorConfig:
    table_name: str = 'rag_vector_documents'
    embedding_dimensions: int = 1536

    def __post_init__(self) -> None:
        if not re.fullmatch(r'[a-z_][a-z0-9_]*', self.table_name):
            raise ValueError('table_name must be a safe SQL identifier')
        if self.embedding_dimensions <= 0:
            raise ValueError('embedding_dimensions must be positive')


class PgVectorStore:
    def __init__(self, *, session: Session, config: PgVectorConfig | None = None) -> None:
        self.session = session
        self.config = config or PgVectorConfig()

    def schema_sql(self) -> list[str]:
        table = self.config.table_name
        dimensions = self.config.embedding_dimensions
        return [
            'CREATE EXTENSION IF NOT EXISTS vector;',
            f"""
            CREATE TABLE IF NOT EXISTS {table} (
                document_id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                source_url TEXT NOT NULL,
                source_snippet TEXT NOT NULL,
                permission_level TEXT NOT NULL,
                metadata_json JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                embedding vector({dimensions}) NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
            """,
            f"""
            CREATE INDEX IF NOT EXISTS {table}_embedding_idx
            ON {table}
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100);
            """,
            f"""
            CREATE INDEX IF NOT EXISTS {table}_permission_idx
            ON {table} (permission_level);
            """,
        ]

    def ensure_schema(self) -> None:
        for statement in self.schema_sql():
            self.session.execute(text(statement))

    def upsert_with_embedding(self, document: VectorDocument, embedding: list[float]) -> None:
        self.session.execute(
            text(self._upsert_sql()),
            {
                'document_id': document.document_id,
                'text': document.text,
                'source_url': document.source_url,
                'source_snippet': document.source_snippet,
                'permission_level': document.permission_level,
                'metadata_json': document.metadata,
                'embedding': _embedding_literal(embedding),
            },
        )

    def search_with_embedding(
        self,
        *,
        query_embedding: list[float],
        user: DemoUser,
        limit: int = 5,
    ) -> VectorSearchResult:
        rows = (
            self.session.execute(
                text(self._search_sql()),
                {
                    'query_embedding': _embedding_literal(query_embedding),
                    'allowed_permissions': _allowed_permissions_for_user(user),
                    'limit': limit,
                },
            )
            .mappings()
            .all()
        )
        matches = [
            VectorMatch(
                document=VectorDocument(
                    document_id=row['document_id'],
                    text=row['text'],
                    source_url=row['source_url'],
                    source_snippet=row['source_snippet'],
                    permission_level=row['permission_level'],
                    metadata=_metadata_from_row(row['metadata_json']),
                ),
                score=float(row['score']),
            )
            for row in rows
        ]
        hidden_match_count = int(rows[0]['hidden_match_count']) if rows else 0
        return VectorSearchResult(matches=matches, hidden_match_count=hidden_match_count)

    def _upsert_sql(self) -> str:
        table = self.config.table_name
        return f"""
        INSERT INTO {table} (
            document_id,
            text,
            source_url,
            source_snippet,
            permission_level,
            metadata_json,
            embedding,
            updated_at
        )
        VALUES (
            :document_id,
            :text,
            :source_url,
            :source_snippet,
            :permission_level,
            :metadata_json,
            CAST(:embedding AS vector),
            now()
        )
        ON CONFLICT (document_id) DO UPDATE SET
            text = EXCLUDED.text,
            source_url = EXCLUDED.source_url,
            source_snippet = EXCLUDED.source_snippet,
            permission_level = EXCLUDED.permission_level,
            metadata_json = EXCLUDED.metadata_json,
            embedding = EXCLUDED.embedding,
            updated_at = now();
        """

    def _search_sql(self) -> str:
        table = self.config.table_name
        return f"""
        WITH ranked AS (
            SELECT
                document_id,
                text,
                source_url,
                source_snippet,
                permission_level,
                metadata_json,
                embedding <=> CAST(:query_embedding AS vector) AS distance,
                1 - (embedding <=> CAST(:query_embedding AS vector)) AS score,
                permission_level = ANY(:allowed_permissions) AS is_visible
            FROM {table}
        ),
        hidden AS (
            SELECT count(*) AS hidden_match_count
            FROM ranked
            WHERE NOT is_visible
        )
        SELECT
            ranked.document_id,
            ranked.text,
            ranked.source_url,
            ranked.source_snippet,
            ranked.permission_level,
            ranked.metadata_json,
            ranked.score,
            hidden.hidden_match_count
        FROM ranked
        CROSS JOIN hidden
        WHERE permission_level = ANY(:allowed_permissions)
        ORDER BY ranked.distance
        LIMIT :limit;
        """


def _embedding_literal(embedding: list[float]) -> str:
    return '[' + ','.join(str(float(value)).rstrip('0').rstrip('.') for value in embedding) + ']'


def _allowed_permissions_for_user(user: DemoUser) -> list[str]:
    if user.role == 'admin':
        return ['public', 'internal', 'restricted']
    return ['public', 'internal']


def _metadata_from_row(value: Any) -> dict:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        parsed = json.loads(value)
        return parsed if isinstance(parsed, dict) else {}
    return {}
