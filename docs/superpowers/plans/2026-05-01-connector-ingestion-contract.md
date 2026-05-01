# Connector Ingestion Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Define a shared connector ingestion contract so Slack, Gmail, Drive, and future live OAuth adapters enter ParaWorks through the same tested path.

**Architecture:** Add connector manifests beside `SourceEvent`, expose a registry for integration metadata, and move sync job orchestration into `backend/app/ingestion/sync.py`. Keep mock connectors as the local/demo implementation while making their shape match the future live adapters.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, existing ParaWorks connector and ingestion packages.

---

### Task 1: Contract Tests

**Files:**
- Create: `backend/tests/test_connector_ingestion_contract.py`

- [x] Write failing tests for connector manifests, shared sync job orchestration, duplicate skip counts, and failed connector status.
- [x] Verify RED against the missing `ConnectorManifest` import.

### Task 2: Connector Manifest Registry

**Files:**
- Modify: `backend/app/connectors/base.py`
- Modify: `backend/app/connectors/mock.py`
- Modify: `backend/app/connectors/slack.py`
- Create: `backend/app/connectors/registry.py`

- [x] Add `ConnectorManifest`.
- [x] Add OAuth-like scopes, sync strategy, and cost policy metadata for mock connectors.
- [x] Expose `list_connector_manifests` and `get_connector_manifest`.
- [x] Keep the live Slack connector compatible with the same manifest shape.

### Task 3: Shared Sync Orchestration

**Files:**
- Create: `backend/app/ingestion/sync.py`
- Modify: `backend/app/api/v1/integrations.py`

- [x] Add `ConnectorSyncResult`.
- [x] Move job creation, connector fetch, event ingestion, duplicate skip counts, and failure status into `sync_connector_events`.
- [x] Update `/api/v1/integrations` to return manifest metadata.
- [x] Update `/api/v1/integrations/{connector_type}/sync` to use the shared sync path.

### Task 4: Verification And Documentation

**Files:**
- Modify: `AGENTS.md`
- Modify: `docs/portfolio-log.md`
- Modify: `frontend/src/app/integrations/page.tsx`
- Modify: `frontend/src/lib/api/types.ts`

- [x] Add assistant/developer guidance for connector ownership boundaries.
- [x] Record the portfolio value and cost-aware ingestion rule.
- [x] Surface connector manifests, scopes, sync strategy, cost policy, fetched counts, and skipped counts in `/integrations`.
- [x] Run focused tests and Ruff.
- [x] Run full backend tests.
- [x] Run frontend build.
- [x] Run smoke API checks for integrations list and sync.
