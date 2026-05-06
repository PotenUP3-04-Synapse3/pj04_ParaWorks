import os
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from backend.app.core.demo_auth import USERS
from backend.app.rag.embeddings import DeterministicHashEmbeddingModel
from backend.app.rag.indexing import index_changed_vector_documents
from backend.app.rag.pgvector_store import PgVectorConfig, PgVectorStore
from backend.app.rag.vector_store import VectorDocument


@pytest.mark.skipif(
    not os.getenv('PARAWORKS_PGVECTOR_TEST_DATABASE_URL'),
    reason='set PARAWORKS_PGVECTOR_TEST_DATABASE_URL to run pgvector integration test',
)
def test_pgvector_reindex_path_with_fake_embedding() -> None:
    engine = create_engine(os.environ['PARAWORKS_PGVECTOR_TEST_DATABASE_URL'])
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    test_id = uuid4().hex[:8]
    table_name = f'rag_vector_documents_test_{test_id}'
    document_id = f'chunk:pgvector-test:{test_id}'

    with session_local() as db:
        store = PgVectorStore(session=db, config=PgVectorConfig(table_name=table_name, embedding_dimensions=8))
        store.ensure_schema()
        db.commit()

        result = index_changed_vector_documents(
            db=db,
            documents=[
                VectorDocument(
                    document_id=document_id,
                    text='PostgreSQL pgvector stores durable company memory embeddings.',
                    source_url='https://pgvector.mock/company-memory',
                    source_snippet='pgvector stores durable company memory',
                    permission_level='internal',
                    metadata={'source_type': 'integration_test'},
                )
            ],
            writer=store,
            embedding_model=DeterministicHashEmbeddingModel(dimensions=8),
            embedding_model_name='deterministic-hash:integration',
        )

        search_result = store.search_with_embedding(
            query_embedding=DeterministicHashEmbeddingModel(dimensions=8).embed('durable company memory'),
            user=USERS['viewer'],
            limit=5,
        )

        assert result.indexed_count == 1
        assert result.embedding_request_count == 1
        assert search_result.matches[0].document.document_id == document_id

        db.execute(text(f'DROP TABLE IF EXISTS {table_name}'))
        db.commit()
