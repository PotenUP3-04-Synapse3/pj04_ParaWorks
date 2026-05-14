# ParaWorks

ParaWorks is a company-wide knowledge and history platform.

This repository starts with an Adapter-First Demo Harness: a local FastAPI backend, Next.js frontend, mock source connectors, review workflow, permission-filtered search, and verification runbooks.

Production RAG storage is oriented around PostgreSQL + pgvector. The Docker
Postgres service uses the `pgvector/pgvector:pg17` image and initializes a
`rag_vector_documents` table for embedding search, while SQLite smoke mode stays
available for fast local demos.

For local pgvector validation, use:

```powershell
.\scripts\start-pgvector-dev.ps1
```

If another PostgreSQL service already owns `127.0.0.1:5432`, the helper falls
back to host port `5432` and prints the matching `DATABASE_URL`. Full details
and the fake-embedding integration test live in
`docs/superpowers/runbooks/pgvector-dev.md`.
