# Azure Integration Design

Updated: 2026-05-03

## Goal

Attach Azure to ParaWorks in three phases without breaking the current harness:

1. Azure deployment foundation.
2. Azure OpenAI-compatible provider alias.
3. Staging deployment preparation.

This spec intentionally avoids creating cloud resources or storing secrets in
the repository.

## Phase 1. Deployment Foundation

Recommended Azure services:

- Azure Container Apps for `frontend`, `backend`, and `worker`.
- Azure Database for PostgreSQL Flexible Server with pgvector enabled.
- Azure Cache for Redis for Celery.
- Azure Key Vault for Slack, Google, OpenAI, Gemini, and future Azure secrets.
- Managed Identity for Container Apps to read Key Vault secrets.

The existing `docs/superpowers/runbooks/deployment.md` remains the production
deployment source of truth. Azure-specific resource names, Key Vault mappings,
and staging URLs should be added there when real resources exist.

## Phase 2. Azure OpenAI-Compatible Alias

The first implementation treats `azure_openai` as an OpenAI-compatible alias,
not as a separate Azure endpoint integration.

Current behavior:

- `AGENT_LLM_PROVIDER_ORDER=azure_openai,openai,gemini` is valid.
- `azure_openai` uses the existing `OPENAI_API_KEY` path.
- `azure_openai` uses the existing OpenAI model setting:
  `AGENT_LLM_OPENAI_MODEL`.
- RAG embeddings continue to use the existing OpenAI-compatible embedding
  client and `OPENAI_API_KEY`.
- No new Azure secrets are required for this first slice.

Why this design:

- The user can swap the API key without changing application code.
- Existing cost controls, preflight, ranked evidence windows, token caps, and
  Gemini fallback stay intact.
- Tests can use fake clients and do not call live OpenAI or Azure APIs.

Future true Azure OpenAI mode:

- Add `AZURE_OPENAI_ENDPOINT`.
- Add `AZURE_OPENAI_API_VERSION`.
- Add chat and embedding deployment names.
- Use Azure-specific SDK or OpenAI client base URL configuration behind the
  same provider contract.
- Keep `azure_openai` as the provider name so the UI/API contract does not
  change.

## Phase 3. Staging Preparation

Before deploying:

- Add Key Vault secret mapping for all provider and OAuth keys.
- Add Container Apps environment variable mapping.
- Add Alembic migrations for production auth and vector tables.
- Verify PostgreSQL pgvector extension.
- Run RAG reindex dry-run before any paid embedding write.
- Run Playwright route regression against staging.

## Cost Policy

- Status APIs must not call paid providers.
- Provider availability checks must inspect configuration only.
- Paid LLM runs still require preflight and explicit confirmation.
- Embedding reindexing must keep hash-skip and budget gates active.

## Security Policy

- No Azure keys, OpenAI keys, Slack tokens, Google secrets, connection strings,
  or Key Vault secret values may be committed.
- Container Apps should read secrets through Key Vault references or Managed
  Identity.
- Production mode must use cookie auth and reject client-supplied demo headers.
