CREATE TABLE IF NOT EXISTS vector_index_states (
    id SERIAL PRIMARY KEY,
    document_id VARCHAR(200) NOT NULL,
    embedding_model VARCHAR(120) NOT NULL,
    embedding_dimensions INTEGER NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'indexed',
    last_error TEXT,
    indexed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_vector_index_state_document_model UNIQUE (document_id, embedding_model)
);

CREATE INDEX IF NOT EXISTS ix_vector_index_states_document_id
    ON vector_index_states (document_id);

CREATE INDEX IF NOT EXISTS ix_vector_index_states_embedding_model
    ON vector_index_states (embedding_model);

CREATE INDEX IF NOT EXISTS ix_vector_index_states_content_hash
    ON vector_index_states (content_hash);

CREATE INDEX IF NOT EXISTS ix_vector_index_states_status
    ON vector_index_states (status);
