# ParaWorks Deployment Runbook

Updated: 2026-05-02

## Deployment Goal

Deploy ParaWorks as a Korean-first company-memory product with:

- Next.js frontend;
- FastAPI backend;
- PostgreSQL with pgvector;
- Redis for Celery queue/broker;
- Celery worker for RAG indexing jobs;
- optional live Slack and Google OAuth integrations;
- explicit budget gates for LLM and embedding calls.

SQLite smoke mode remains for demos and local verification only.

## Runtime Components

Required production components:

- `frontend`: Next.js app.
- `backend`: FastAPI app served by uvicorn/gunicorn.
- `postgres`: PostgreSQL with `vector` extension enabled.
- `redis`: Celery broker/result backend.
- `worker`: Celery worker running `backend.app.tasks.rag_indexing`.

Optional components:

- object storage for exported Drive files and parser artifacts;
- background scheduler for recurring sync;
- observability stack for logs, traces, and metrics.

## Azure Target Mapping

The recommended Azure staging target is:

- Azure Container Apps: `frontend`, `backend`, and `worker`.
- Azure Database for PostgreSQL Flexible Server with pgvector.
- Azure Cache for Redis.
- Azure Key Vault for all OAuth, provider, database, and session secrets.
- Managed Identity so Container Apps can read Key Vault secret references.

Do not create resources from this runbook without first confirming budget,
region, resource group, and staging domain.

## Environment Variables

Core:

- `PARAWORKS_DEMO_MODE=false`
- `DATABASE_URL=postgresql+psycopg://...`
- `REDIS_URL=redis://...`
- `NEXT_PUBLIC_API_BASE_URL=https://api.example.com`

Auth:

- production cookie/session secrets;
- OAuth client ids and secrets;
- allowed callback origins.

Slack:

- `SLACK_CLIENT_ID`
- `SLACK_CLIENT_SECRET`
- `SLACK_OAUTH_REDIRECT_URI`
- `SLACK_OAUTH_STATE_SECRET`

Google:

- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_OAUTH_REDIRECT_URI`
- `GOOGLE_OAUTH_STATE_SECRET`

LLM and embedding:

- `OPENAI_API_KEY`
- `AGENT_LLM_PROVIDER_ORDER=azure_openai,openai,gemini` for the current
  OpenAI-compatible Azure alias path.
- `GEMINI_API_KEY`
- `RAG_USE_PGVECTOR_SEARCH=true`
- `RAG_EMBEDDING_MAX_ESTIMATED_COST_USD`
- `AGENT_LLM_MAX_ESTIMATED_COST_USD`

Never commit real secrets.

Current Azure OpenAI-compatible note:

- The first `azure_openai` provider alias intentionally uses the existing
  `OPENAI_API_KEY` path so a key swap works without code changes.
- True Azure OpenAI endpoint/deployment mode still needs future variables such
  as endpoint, API version, and deployment names.

## Database Setup

1. Create the PostgreSQL database.
2. Enable pgvector:

   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

3. Run Alembic migrations.
4. Confirm the vector index table exists:

   ```sql
   SELECT to_regclass('rag_vector_documents');
   ```

5. Confirm the app can connect:

   ```powershell
   python -m backend.app.db.init_db
   ```

## Deployment Order

1. Build and deploy database migrations.
2. Deploy backend.
3. Deploy worker with the same backend image and environment.
4. Deploy frontend with `NEXT_PUBLIC_API_BASE_URL` pointing at the backend.
5. Verify `/health`.
6. Verify `/api/v1/orchestration/status`.
7. Verify `/api/v1/rag/indexing/summary`.
8. Run a dry-run RAG reindex before real embedding writes.
9. Connect Slack/Google OAuth in a staging workspace first.
10. Run Playwright smoke checks against staging.

## Verification Commands

Backend:

```powershell
python -m ruff check backend
python -m pytest backend/tests -q
```

Frontend:

```powershell
cd frontend
npm.cmd run lint
npm.cmd run build
npm.cmd run test:visual -- e2e/page-regression.spec.ts
```

Runtime smoke:

```powershell
Invoke-RestMethod https://api.example.com/health
Invoke-RestMethod https://api.example.com/api/v1/orchestration/status
```

## Cost Gates

Production must keep these gates active:

- status APIs do not call paid LLMs;
- sync APIs do not call paid LLMs;
- embedding reindex has dry-run preflight;
- changed-content hash skips unchanged vectors;
- Slack/Gmail/Drive/Calendar evidence windows are ranked and bounded;
- confirmed paid agent runs record estimated and actual cost;
- provider fallback does not silently double-call unless the primary fails.

## Rollback Plan

1. Stop new sync and agent-run triggers.
2. Keep Review Queue and Knowledge pages read-only.
3. Roll backend and worker to the previous image.
4. Roll frontend to the previous image.
5. If a migration is involved, prefer forward-fix migrations. Only rollback
   schema when the migration is explicitly reversible and data-safe.
6. Preserve audit logs and AgentRun records for incident review.

## Monitoring

Track:

- API error rate and latency;
- sync job status and failures;
- Celery queue depth;
- embedding request count and skipped count;
- LLM estimated vs actual cost;
- RAG hidden-match count;
- Review Queue pending/needs-more-evidence backlog;
- OAuth callback errors.

## Production Readiness Checklist

- `PARAWORKS_DEMO_MODE=false`.
- Demo `X-Demo-User` auth disabled.
- httpOnly cookie auth enabled.
- Postgres + pgvector active.
- Redis and worker active.
- OAuth redirect URIs match deployed frontend domain.
- Secrets stored in deployment secret manager.
- RAG reindex dry-run is within budget.
- Playwright page regression passes on staging.
- Rollback image is known.
