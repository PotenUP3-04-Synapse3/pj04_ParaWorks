from backend.app.api.v1 import search as search_api
from backend.app.core.demo_auth import DemoUser
from backend.app.rag.vector_store import VectorDocument, VectorMatch, VectorSearchResult


def test_search_response_discloses_default_deterministic_retrieval_backend(client) -> None:
    client.post('/api/v1/integrations/gmail/sync')

    response = client.post('/api/v1/search', json={'query': 'Redis job state'})

    assert response.status_code == 200
    payload = response.json()
    assert payload['retrieval_backend'] == 'deterministic_lexical'
    assert payload['cost_policy'] == {
        'embedding_query_call': False,
        'paid_llm_call': False,
        'requires_pgvector_flag': True,
    }
    assert payload['results']


def test_search_uses_pgvector_adapter_when_available(client, monkeypatch) -> None:
    class FakeVectorStore:
        def search(self, *, query: str, user: DemoUser, limit: int = 5) -> VectorSearchResult:
            assert query == 'Redis vector query'
            assert user.id == 'employee-mina'
            assert limit == 5
            return VectorSearchResult(
                matches=[
                    VectorMatch(
                        document=VectorDocument(
                            document_id='vector:gmail-redis',
                            text='Redis vector result text',
                            source_url='https://gmail.mock/vector-redis',
                            source_snippet='Redis vector snippet',
                            permission_level='internal',
                            metadata={
                                'source_type': 'gmail',
                                'author': 'owner@example.com',
                                'timestamp': '2026-05-02T09:00:00+09:00',
                                'matched_terms': ['redis'],
                            },
                        ),
                        score=0.88,
                    )
                ],
                hidden_match_count=1,
            )

    monkeypatch.setattr(search_api, '_pgvector_search_store', lambda *, db, settings: FakeVectorStore())

    response = client.post(
        '/api/v1/search',
        headers={'X-Demo-User': 'viewer'},
        json={'query': 'Redis vector query'},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload['retrieval_backend'] == 'pgvector'
    assert payload['hidden_match_count'] == 1
    assert payload['permission_notice'] == 'Some sources may be hidden by permissions.'
    assert payload['cost_policy'] == {
        'embedding_query_call': True,
        'paid_llm_call': False,
        'requires_pgvector_flag': True,
    }
    assert payload['results'][0]['source_id'] == 'vector:gmail-redis'
    assert payload['results'][0]['relevance_score'] == 0.88
    assert payload['results'][0]['matched_terms'] == ['redis']
