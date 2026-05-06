# pgvector RAG Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make PostgreSQL + pgvector the explicit production RAG storage target while preserving SQLite smoke mode.

**Architecture:** Keep the existing in-memory vector store for deterministic tests and local smoke flows. Add a separate `PgVectorStore` adapter that owns pgvector DDL, upsert SQL, permission-filtered similarity search SQL, and Docker init SQL for new Postgres databases.

**Tech Stack:** PostgreSQL, pgvector, SQLAlchemy, psycopg, pytest, Docker Compose.

---

### Task 1: Lock pgvector Adapter Contract

**Files:**
- Create: `backend/tests/test_pgvector_store.py`

- [x] **Step 1: Write failing tests**

Tests assert:

- Docker init SQL creates `rag_vector_documents`.
- Schema SQL enables `vector`, creates `embedding vector(1536)`, ivfflat cosine index, and permission index.
- Upsert SQL writes `VectorDocument` with pgvector embedding literal.
- Search SQL filters by allowed permissions and returns hidden match counts.

- [x] **Step 2: Verify RED**

Run: `uv run pytest backend/tests/test_pgvector_store.py -v`

Expected: missing `backend.app.rag.pgvector_store`.

### Task 2: Implement pgvector Adapter

**Files:**
- Create: `backend/app/rag/pgvector_store.py`
- Modify: `backend/app/rag/__init__.py`
- Create: `docker/postgres/init/002_rag_vector_documents.sql`

- [x] **Step 1: Add `PgVectorConfig`**

The config validates the table name and embedding dimension.

- [x] **Step 2: Add `PgVectorStore`**

The store exposes:

- `schema_sql()`
- `ensure_schema()`
- `upsert_with_embedding()`
- `search_with_embedding()`

- [x] **Step 3: Add Docker init SQL**

New Postgres containers create the vector document table and indexes at startup.

### Task 3: Verification and Documentation

**Files:**
- Modify: `AGENTS.md`
- Modify: `README.md`
- Modify: `docs/portfolio-log.md`

- [x] **Step 1: Document the decision**

Record PostgreSQL + pgvector as the default production RAG store.

- [x] **Step 2: Run verification**

Run:

- `uv run pytest backend/tests/test_pgvector_store.py -v`
- `uv run pytest backend/tests -v`
- `npm.cmd run build`
- smoke HTTP checks

- [x] **Step 3: Commit**

Commit message: `feat: add pgvector rag adapter`
