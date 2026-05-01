from backend.app.core.demo_auth import USERS
from backend.app.rag.pgvector_store import PgVectorConfig, PgVectorStore
from backend.app.rag.vector_store import VectorDocument


def test_docker_postgres_init_creates_pgvector_rag_table() -> None:
    sql = open('docker/postgres/init/002_rag_vector_documents.sql', encoding='utf-8').read()

    assert 'CREATE TABLE IF NOT EXISTS rag_vector_documents' in sql
    assert 'embedding vector(1536)' in sql
    assert 'USING ivfflat (embedding vector_cosine_ops)' in sql
    assert 'rag_vector_documents_permission_idx' in sql


class RecordingSession:
    def __init__(self, rows=None) -> None:
        self.calls = []
        self._rows = rows or []

    def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        return RecordingResult(self._rows)


class RecordingResult:
    def __init__(self, rows) -> None:
        self._rows = rows

    def mappings(self):
        return self

    def all(self):
        return self._rows


def test_pgvector_schema_sql_creates_extension_table_and_indexes() -> None:
    store = PgVectorStore(session=RecordingSession(), config=PgVectorConfig(embedding_dimensions=1536))

    schema_sql = '\n'.join(store.schema_sql())

    assert 'CREATE EXTENSION IF NOT EXISTS vector' in schema_sql
    assert 'embedding vector(1536)' in schema_sql
    assert 'rag_vector_documents_embedding_idx' in schema_sql
    assert 'vector_cosine_ops' in schema_sql
    assert 'rag_vector_documents_permission_idx' in schema_sql


def test_pgvector_upsert_writes_document_with_embedding_literal() -> None:
    session = RecordingSession()
    store = PgVectorStore(session=session)

    store.upsert_with_embedding(
        VectorDocument(
            document_id='knowledge:decision:1',
            text='Use Redis for queue state.',
            source_url='knowledge://decision_record:1',
            source_snippet='Use Redis for queue state.',
            permission_level='internal',
            metadata={'source_type': 'decision_record'},
        ),
        embedding=[0.1, 0.2, 0.3],
    )

    statement, params = session.calls[0]
    assert 'INSERT INTO rag_vector_documents' in statement
    assert 'ON CONFLICT (document_id) DO UPDATE' in statement
    assert params['document_id'] == 'knowledge:decision:1'
    assert params['embedding'] == '[0.1,0.2,0.3]'
    assert params['metadata_json'] == {'source_type': 'decision_record'}


def test_pgvector_search_filters_by_user_permission_and_tracks_hidden_matches() -> None:
    rows = [
        {
            'document_id': 'gmail:redis',
            'text': 'Redis queue state',
            'source_url': 'https://gmail.mock/redis',
            'source_snippet': 'Redis queue state',
            'permission_level': 'internal',
            'metadata_json': {'source_type': 'gmail'},
            'score': 0.92,
            'hidden_match_count': 1,
        }
    ]
    session = RecordingSession(rows=rows)
    store = PgVectorStore(session=session)

    result = store.search_with_embedding(query_embedding=[0.3, 0.2, 0.1], user=USERS['viewer'], limit=5)

    statement, params = session.calls[0]
    assert 'permission_level = ANY(:allowed_permissions)' in statement
    assert 'embedding <=> CAST(:query_embedding AS vector)' in statement
    assert params['allowed_permissions'] == ['public', 'internal']
    assert params['query_embedding'] == '[0.3,0.2,0.1]'
    assert result.hidden_match_count == 1
    assert [match.document.document_id for match in result.matches] == ['gmail:redis']
    assert result.matches[0].score == 0.92
