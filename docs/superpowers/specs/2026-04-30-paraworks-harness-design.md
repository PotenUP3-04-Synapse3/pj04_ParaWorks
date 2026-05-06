# ParaWorks Harness Design

**Date:** 2026-04-30
**Project:** ParaWorks
**Source Plan:** `C:\Users\user\Downloads\deep_knowlogy\plan\plan-merged-v0.md`
**Target Repository:** `C:\potenup3\pj04-Paraworks`

## Purpose

This design defines the first service-building harness for ParaWorks. The harness combines:

1. A local development/runtime harness for starting the service skeleton.
2. A mock-data demo harness for validating the MVP workflow before real Google, Slack, Gmail, and Calendar integrations exist.
3. A Codex work harness for breaking the large product plan into reviewable implementation tasks.

The design follows the plan's product direction: ParaWorks is a company-wide knowledge and history platform, not a team task manager. Streamlit is removed. The service is built around FastAPI, PostgreSQL with pgvector, Redis, Celery, MinIO-compatible object storage, and a Next.js 15 App Router frontend.

## Goals

- Make the repository runnable locally with a small, dependable service skeleton.
- Validate the core ParaWorks workflow using deterministic mock data.
- Keep future real integrations easy to add through connector interfaces.
- Preserve security-critical behavior from the start: source evidence, review status, permission filtering, and auditability.
- Give Codex a clear spec/plan/task/verification operating model.

## Non-Goals

- Implement real Google Drive, Gmail, Slack, or Google Calendar API access in the first harness.
- Implement production SSO or final auth token storage.
- Implement a full LangGraph agent pipeline in the first pass.
- Implement advanced Knowledge Map visualization.
- Build GitHub integration, external customer data isolation, or C-level report generation.

## Recommended Approach

Use an Adapter-First Demo Harness.

FastAPI, Next.js, Docker Compose, PostgreSQL, Redis, and MinIO form the local runtime. External data sources are represented by mock connectors first. Real connectors later implement the same contract as the mock connectors, so the ingestion, review, search, and permission layers do not need to be rewritten.

This approach is preferred over a backend-only harness because ParaWorks depends heavily on review and source evidence workflows that need UI validation. It is preferred over a full MVP skeleton because it avoids creating wide but shallow code for unsettled policy areas.

## Architecture

```text
[Next.js 15 Demo UI]
        |
        | REST API / SSE
        v
[FastAPI Backend]
        |
        +--> API Routes
        +--> Mock Connector Interfaces
        +--> Ingestion Pipeline
        +--> Deterministic Knowledge Extraction
        +--> Permission Guard
        +--> Review Queue
        +--> Audit/Job Status
        |
        v
[PostgreSQL + pgvector] [Redis] [MinIO]
```

The first harness should run without external SaaS credentials. `.env.example` documents future configuration, but demo mode should work from local seed data.

## Backend Components

### Connectors

`backend/app/connectors/` owns all source-specific integration boundaries.

Initial implementations:

- `MockDriveConnector`
- `MockGmailConnector`
- `MockSlackConnector`
- `MockCalendarConnector`

Each connector returns normalized source events with metadata required by downstream layers:

- `source_type`
- `source_id`
- `source_url`
- `title`
- `body`
- `author`
- `participants`
- `timestamp`
- `permission_level`
- `raw_metadata`

Later real integrations should be added beside the mock connectors, not inside ingestion or API routes.

### Ingestion

`backend/app/ingestion/` turns connector events into internal records:

- `Source`
- `Document`
- `DocumentVersion`
- `DocumentChunk`
- `SyncJob`
- `ParserRun`

The ingestion layer enforces source metadata, idempotency by source identity, and preservation of source evidence.

### Knowledge Extraction

`backend/app/knowledge/` creates deterministic demo candidates from chunks. This replaces LLM agents in the first harness while keeping the future shape of the system.

Generated candidates:

- `DecisionRecord`
- `HistoryEvent`
- `TimelineEvent`
- `Todo`

Every generated candidate must include:

- `source_links`
- `source_snippets`
- `confidence_score`
- `review_status="pending_review"`
- `permission_level`

Candidates without source evidence must not be approvable.

### Review Queue

`ReviewItem` is the control point between AI-generated/demo-generated candidates and official knowledge records.

Supported actions:

- Approve
- Reject
- Edit
- Request more evidence
- View sources

The first harness should store generated records as pending review items and only expose approved records as trusted knowledge in search and dashboard summaries.

### Permission Guard

`backend/app/permissions/` filters both retrieval inputs and API outputs. The permission model combines source permission metadata with a simple ParaWorks RBAC layer.

The first harness must include a permission leakage scenario where an unauthorized source exists in the database but is hidden from search results and source evidence output for a restricted user.

### Job Status and SSE

Integration sync creates a `SyncJob`. `/api/v1/stream/job-status?job_id=...` emits progress events for the frontend.

Demo status stages:

- queued
- fetching mock source events
- normalizing source records
- creating chunks
- generating review candidates
- complete
- failed

## Backend API Scope

Initial endpoints:

- `GET /health`
- `GET /api/v1/dashboard`
- `POST /api/v1/integrations/{type}/sync`
- `GET /api/v1/integrations`
- `GET /api/v1/stream/job-status?job_id=`
- `POST /api/v1/search`
- `GET /api/v1/review?status=pending_review`
- `POST /api/v1/review/{item_id}/approve`
- `POST /api/v1/review/{item_id}/reject`
- `PATCH /api/v1/review/{item_id}`
- `POST /api/v1/review/{item_id}/request-more-evidence`

Auth can begin with a demo user selected by request header or local demo state. The code should keep auth boundaries clear so Google Workspace OAuth can replace demo auth later.

## Frontend Scope

The first Next.js harness includes four app screens.

### `/dashboard`

Shows:

- source counts by type
- pending review count
- recent approved decisions
- recent todos
- recent sync jobs

### `/integrations`

Shows mock connector cards for Drive, Gmail, Slack, and Calendar. Each card can start a demo sync and display sync progress through SSE.

### `/review`

Shows pending review items with source evidence, confidence score, permission notice, and approve/reject/edit/request-more-evidence controls.

### `/search`

Shows permission-filtered search results with snippets and a Source Evidence Drawer. Unauthorized source content must not appear.

## File Structure

```text
C:\potenup3\pj04-Paraworks
  docker-compose.yml
  .env.example
  backend/
    app/
      main.py
      core/
      db/
      models/
      schemas/
      api/v1/
      connectors/
      ingestion/
      knowledge/
      permissions/
      seeds/
      workers/
    tests/
  frontend/
    src/
      app/
      components/
      lib/
      hooks/
      stores/
  docs/
    superpowers/
      specs/
      plans/
      decisions/
      runbooks/
```

## Demo Data Scenarios

### `project-alpha-redis-decision`

Slack, Gmail, and Drive mock records support a decision to use Redis. The generated Decision Record should explain the situation, alternatives, constraints, final decision, participants, and source snippets.

### `project-beta-scope-cut`

Calendar and Slack mock records support a feature scope reduction. The generated History Event and Todo should explain why a feature was excluded and what follow-up remains.

### `permission-leakage-case`

A restricted Drive document is present in the database. A viewer without source permission cannot see its chunks, snippets, summaries, or search-derived answer content.

## Data Flow

1. A user starts a mock sync from `/integrations`.
2. FastAPI creates a `SyncJob` and returns `job_id`.
3. The frontend opens the SSE job-status stream.
4. A mock connector returns source events.
5. Ingestion normalizes events into source and chunk records.
6. Deterministic knowledge extraction creates candidates.
7. Validation checks evidence and permission metadata.
8. Candidates are stored as `ReviewItem(status="pending_review")`.
9. A user approves, rejects, edits, or requests more evidence in `/review`.
10. `/search` returns only records and chunks the current user may access.
11. Source Evidence Drawer displays source URLs, snippets, confidence, and permission notices.

## Codex Work Harness

Implementation work should follow this operating model:

```text
spec -> implementation plan -> task -> failing test -> implementation -> verification -> commit
```

Required docs:

```text
docs/superpowers/specs/2026-04-30-paraworks-harness-design.md
docs/superpowers/plans/2026-04-30-paraworks-harness.md
docs/superpowers/decisions/ADR-0001-adapter-first-demo-harness.md
docs/superpowers/runbooks/local-dev.md
docs/superpowers/runbooks/demo-seed.md
docs/superpowers/runbooks/verification.md
```

Initial task breakdown:

1. Phase 0 cleanup: remove Streamlit and unrelated ML dependencies, keep Python 3.12 and uv.
2. Local runtime harness: add Docker Compose, `.env.example`, PostgreSQL with pgvector, Redis, MinIO, and health check.
3. Backend domain skeleton: add SQLAlchemy models, Pydantic schemas, and Alembic foundation.
4. Mock connectors: add Drive, Gmail, Slack, Calendar connectors and seed fixtures.
5. Ingestion and review pipeline: normalize source records and create pending review items.
6. Search and permission guard: implement permission-filtered search and leakage tests.
7. SSE job status: expose mock sync progress.
8. Frontend MVP harness: implement dashboard, search, review, and integrations pages.
9. Verification harness: backend tests, frontend build, permission leakage test, and smoke runbook.

## Verification Requirements

The harness is complete when these checks pass:

- `GET /health` returns a successful response.
- Docker services start locally for PostgreSQL, Redis, and MinIO.
- Mock sync creates source records, chunks, generated candidates, and pending review items.
- Search returns source evidence for accessible sources.
- Search excludes unauthorized source content in the permission leakage scenario.
- Review approve changes an item from `pending_review` to `approved`.
- Review reject changes an item from `pending_review` to `rejected`.
- SSE emits sync progress and completion.
- `frontend` builds successfully.
- The runbooks explain how to start, seed, demo, and verify the harness.

## Risks and Controls

| Risk | Control |
|---|---|
| Real integrations leak into core logic | Keep all external APIs behind connector contracts. |
| Demo records become trusted automatically | Store generated records as pending review items only. |
| Permission leakage | Filter during retrieval and response shaping; include a dedicated leakage test. |
| LLM behavior is hard to test early | Use deterministic mock extraction before adding LangGraph agents. |
| Frontend grows too broad | Limit first harness to dashboard, integrations, review, and search. |
| Auth choice changes later | Use a small demo auth adapter and keep route dependencies replaceable. |

## Open Decisions Deferred From Product Plan

These product decisions remain deferred and should not block the first harness:

- Final company domain list.
- External customer data retention, masking, and deletion policy.
- Slack private channel approval process.
- Rank-based History access policy.
- Azure deployment target.
- Final auth token strategy.
- Final HWP parser choice.
- Whether advanced Knowledge Map belongs in MVP.

## Approval Status

The user approved:

- Adapter-First Demo Harness as the architecture.
- Backend and frontend component boundaries.
- Mock-data data flow and seed scenarios.
- Codex work harness structure.
