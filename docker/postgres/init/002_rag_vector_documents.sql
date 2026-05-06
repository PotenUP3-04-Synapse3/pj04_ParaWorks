CREATE TABLE IF NOT EXISTS rag_vector_documents (
    document_id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    source_url TEXT NOT NULL,
    source_snippet TEXT NOT NULL,
    permission_level TEXT NOT NULL,
    metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    embedding vector(1536) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS rag_vector_documents_embedding_idx
ON rag_vector_documents
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

CREATE INDEX IF NOT EXISTS rag_vector_documents_permission_idx
ON rag_vector_documents (permission_level);
