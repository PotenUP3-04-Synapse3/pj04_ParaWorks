# ParaWorks Harness Session Handoff

Updated: 2026-05-13

## 2026-05-13 RAG Orchestrator Assistant Handoff

- Active branch: `codex/rag-orchestrator-assistant-memory`.
- Latest pushed commit before this handoff update:
  `506b257 fix: surface Gmail send failures`.
- Current local serious mode status:
  - backend: `http://127.0.0.1:8000`
  - frontend: `http://127.0.0.1:3000`
  - backend health returned `demo_mode=false`.
- Gmail runtime status checked during the session:
  - Gmail integration was connected;
  - credential status was available for `hanvv3@koreacu.ac.kr`.
- Email-send approval flow investigation:
  - `/search` already calls
    `POST /api/v1/assistant/messages/{messageId}/email/send` when a user
    approves a pending email draft.
  - The backend send path goes through
    `backend/app/assistant/gmail_sender.py`.
  - The sender requires a connected Gmail integration, `gmail.send` scope, a
    stored token in `.tokens.json`, and refresh-token credentials when the
    access token is expired.
  - The local backend had been running without reload, so changed backend code
    required a server restart before the send endpoint could reflect updates.
- Implemented in commit `506b257`:
  - Added focused tests in `backend/tests/test_gmail_sender.py`.
  - Gmail API send failures now surface as explicit `GmailSendError` codes such
    as `gmail_api_send_failed:403` instead of becoming opaque runtime errors.
  - Gmail refresh failures now surface as explicit error codes such as
    `gmail_refresh_failed:{status}` and `gmail_refresh_unreachable`.
  - `/search` maps backend email-send error codes to Korean user-facing
    messages so the user can tell whether the problem is missing connection,
    missing `gmail.send` scope, missing token, refresh failure, or Gmail API
    rejection.
- Verification completed for that commit:

```powershell
uv run pytest backend/tests/test_assistant_api.py backend/tests/test_gmail_sender.py -q
cd frontend
npm.cmd run lint
npm.cmd run build
git diff --check
```

Result:

- backend targeted tests: 14 passed;
- frontend lint: passed with an existing warning in
  `frontend/src/app/projects/page.tsx` about unused `projectSeedData`;
- frontend build: passed;
- whitespace check: passed.

Next recommended steps:

1. Reproduce the approve-send flow in the browser after logging in with the
   Gmail-connected account.
2. If sending still fails, capture the backend response body from the
   `/api/v1/assistant/messages/{messageId}/email/send` request. The new error
   code should now point to the exact missing OAuth/token/Gmail API condition.
3. If the error is `gmail_send_scope_required`, reconnect Gmail after the
   expanded `gmail.send` scope change so Google issues a token with send
   permission.
4. If the error is `gmail_api_send_failed:403`, check Google Cloud OAuth app
   verification/test-user status and Gmail API enablement.

## 2026-05-12 Demo Data Boundary Update

- Default settings now use `PARAWORKS_DEMO_MODE=false` and
  `PARAWORKS_SEED_DEMO_DATA=false`.
- Smoke mode is the only intended path for seeded dummy content:
  `scripts/start-smoke.ps1` sets both demo mode and seed demo data to true.
- Docker/pgvector dev mode (`scripts/start-pgvector-dev.ps1`) starts the app
  with demo mode and seed demo data disabled. With no Slack or Google connection
  installed, the product should show empty states rather than mock business
  content.
- Production-like connector sync must not fall back to mock connectors. It now
  returns a clear not-connected error until OAuth/credentials are available.
- The Review page no longer displays hard-coded fallback review items when the
  API fails or returns no items.
- Dashboard, Projects, and Timeline no longer render sample ORION/Nova/Atlas
  items as visible product data when no connector-backed data exists.

Verification from this session:

```powershell
uv run pytest backend/tests -v
cd frontend
npm run build
```

Result: backend 297 passed, 1 skipped; frontend build passed.

## Active Project

- Repository: `C:\Users\hanvv\Study\potenup3\pj04_ParaWorks`
- Plan draft: `C:\Users\hanvv\Downloads\plan-merged.md`
- Primary spec: `docs/superpowers/specs/2026-04-30-paraworks-harness-design.md`
- Implementation plan: `docs/superpowers/plans/2026-04-30-paraworks-harness.md`
- Assistant guide: `AGENTS.md`
- Portfolio log: `docs/portfolio-log.md`
- Current browser URL during handoff: `http://127.0.0.1:3000/dashboard`

## Product Alignment

ParaWorks is currently aligned as an Adapter-First Demo Harness for a company-wide knowledge and decision-history platform. It is not a team task manager and not a Streamlit app.

The MVP harness keeps real SaaS integrations behind connector contracts and validates the core workflow with mock Drive, Gmail, Slack, and Calendar data:

1. Start mock sync from the frontend.
2. FastAPI creates a sync job.
3. SSE streams job status.
4. Ingestion normalizes source events.
5. Deterministic extraction creates pending review items.
6. Review UI exposes evidence, approve/reject/edit/request-more-evidence actions.
7. Search returns permission-filtered source evidence.

## 2026-05-12 AI 비서 ChatGPT-style Polish and RAG LLM Handoff

- Active branch for this work: `codex/rag-orchestrator-assistant-memory`.
- `/search` is now the primary AI 비서 surface and should feel closer to a
  natural ChatGPT-style conversation:
  - the left history shows compact conversation titles only;
  - `+` reuses an existing empty `새 대화` instead of creating duplicates;
  - evidence and source details live inside each assistant message behind a
    fold/unfold control;
  - the input composer remains at the bottom of the chat surface while evidence
    scrolls inside its own bounded panel.
- Assistant conversations remain database-backed per logged-in user through
  `assistant_conversations` and `assistant_messages`.
- In demo mode, RAG answering stays deterministic for smoke tests and cheap
  demos.
- In non-demo 진심모드, RAG answering builds a real LangChain model chain:
  - primary OpenAI model: `gpt-5.4-mini`;
  - fallback OpenAI model: value from `AGENT_LLM_OPENAI_MODEL` in `.env`;
  - provider fallback continues through `AGENT_LLM_PROVIDER_ORDER`, including
    Gemini when `GEMINI_API_KEY` or `GOOGLE_API_KEY` is configured.
- For another local machine to continue this branch, pull the branch, run
  `uv sync`, `cd frontend && npm.cmd ci`, then set `.env` for 진심모드 with
  `PARAWORKS_DEMO_MODE=false`, `OPENAI_API_KEY`, and optional
  `AGENT_LLM_OPENAI_MODEL` fallback before starting Docker.
- Additional 2026-05-13 UI refinements:
  - conversation history order is based on `updated_at`, not click selection;
  - only the chat transcript pane scrolls when the viewport is short;
  - user messages render as rounded full pills without a `나` label;
  - assistant role/permission badges were removed from message bodies;
  - assistant answers render basic markdown and both user/assistant messages
    expose a small copy action;
  - recommended rounded-full prompt chips above the composer send immediately
    when clicked.

## Latest Session Changes

- Fixed frontend dependency drift by reinstalling `frontend/node_modules` from `package-lock.json` with `npm.cmd ci`.
- Added `outputFileTracingRoot` in `frontend/next.config.ts` so Next does not infer `C:\Users\hanvv` as the workspace root because of an upper-level `package-lock.json`.
- Fixed `frontend/src/hooks/useJobStatus.ts` so a normal SSE `done` event closes the stream without being overwritten by `job stream unavailable`.
- Updated `.gitignore` for local generated files:
  - `.tmp/`
  - `frontend/tsconfig.tsbuildinfo`
  - existing local env ignores

## Verification Completed

Backend:

```powershell
uv run pytest backend/tests -v
```

Result: 18 passed.

Frontend:

```powershell
cd frontend
npm.cmd run build
```

Result: build passed with Next.js 15.5.15.

Browser smoke test used the in-app browser and an SQLite smoke DB because Docker is not available on PATH in this environment.

Verified pages and flows:

- `/integrations`: Slack mock sync runs.
- SSE job stream displays completion JSON.
- Sync creates 3 pending review items on a fresh smoke DB.
- `/review`: review items render.
- Evidence drawer opens and shows source snippets/links.
- `/search`: viewer Redis search returns accessible Slack evidence.
- `/dashboard`: source, pending review, and recent job counts render.

## Runtime State Left Running

At the end of the latest session, local servers were started for manual inspection:

- Frontend: `http://127.0.0.1:3000`
- Backend: `http://127.0.0.1:8000`

The backend was started against a temporary SQLite DB:

```powershell
DATABASE_URL=sqlite:///./.tmp/paraworks-smoke-fresh.db
```

If a later session needs a clean smoke run, create a new `.tmp/*.db` file or delete the old one.

## Important Environment Notes

- `docker` is not currently recognized in PATH, so `docker compose config` and Postgres/Redis/MinIO runtime verification could not be completed.
- Backend tests pass in the real environment with `uv run`; sandboxed runs may fail with local uv cache or Python spawn permission errors.
- `next dev` can enter a stale `.next` state if `npm.cmd run build` is run while the dev server is still active. Restart `next dev` after production builds.
- The frontend depends on Next 15 according to `package.json` and `package-lock.json`. If `npm ls next` shows Next 16, run `npm.cmd ci` from `frontend`.

## Current Git Status To Expect

Expected modified files from the latest session:

- `.gitignore`
- `frontend/next.config.ts`
- `frontend/src/hooks/useJobStatus.ts`

Expected untracked file:

- `frontend/.env.local.example`

Generated files under `.tmp/`, `.next/`, and `frontend/tsconfig.tsbuildinfo` should be ignored.

## Suggested Next Steps

1. Install or expose Docker Desktop/CLI if full Postgres + Redis + MinIO verification is required.
2. Add a frontend regression test for the SSE hook behavior, especially that `done` does not become `job stream unavailable`.
3. Move Messenger messages from in-memory mock state to database-backed persistence.
4. Connect Messenger actions to Review/Knowledge workflows.

## 2026-05-01 Korean I18n and Messenger Update

Added a Korean-first UX pass and Slack-like mock Messenger MVP.

- Spec: `docs/superpowers/specs/2026-05-01-korean-i18n-messenger-design.md`
- Plan: `docs/superpowers/plans/2026-05-01-korean-i18n-messenger.md`
- Backend API:
  - `GET /api/v1/messages/channels`
  - `GET /api/v1/messages/channels/{channel_id}/messages`
  - `POST /api/v1/messages/channels/{channel_id}/messages`
- Frontend:
  - Korean default shell labels.
  - Korean/English language switch in desktop sidebar and mobile header.
  - New `/messages` screen with channels, message timeline, and composer.
  - Existing dashboard, integrations, review, search chrome converted to Korean-first copy.

Verification:

```powershell
uv run pytest backend/tests -v
cd frontend
npm.cmd run build
```

Result: backend 22 tests passed; frontend build passed.

Browser smoke covered:

- Open `/messages`.
- Verify Korean default labels and Korean business channel seed data.
- Switch to English with the mobile `EN` control.
- Post a message and see it appended to the current channel.

## 2026-05-01 SQLite Smoke Mode Update

Added a Docker-free smoke mode for quick product review and browser testing.

- Runbook: `docs/superpowers/runbooks/sqlite-smoke.md`
- Script: `scripts/start-smoke.ps1`
- Updated:
  - `docs/superpowers/runbooks/local-dev.md`
  - `docs/superpowers/runbooks/verification.md`

Use:

```powershell
.\scripts\start-smoke.ps1
```

This initializes `.tmp/paraworks-smoke.db`, starts FastAPI on
`http://127.0.0.1:8000`, and starts Next.js on `http://127.0.0.1:3000`.

## 2026-05-01 Messenger Persistence Update

Moved Messenger from process memory to SQLAlchemy-backed persistence.

- Model: `backend/app/models/messages.py`
- Service: `backend/app/messages/service.py`
- Test: `backend/tests/test_messages.py`

Tables:

- `message_channels`
- `messages`

The message service seeds the three demo channels and their initial messages
when the first message endpoint is called against an empty database. Posted
messages are inserted into `messages`, so they survive page reloads and remain
available while the same SQLite/Postgres database is used.

Verification:

```powershell
uv run pytest backend/tests -v
cd frontend
npm.cmd run build
```

Result after this update: backend 23 tests passed; frontend build passed.

## 2026-05-01 Messenger to Review Queue Update

Connected Messenger to the Review workflow.

- API: `POST /api/v1/messages/messages/{message_id}/send-to-review`
- UI: `/messages` now shows `검토 큐로 보내기` on each message.
- Created review items use:
  - `item_type="message_review"`
  - `payload.title="메신저 검토 요청"`
  - `source_links=["paraworks://messages/{message_id}"]`
  - `source_snippets=[message.body]`

Verification:

```powershell
uv run pytest backend/tests -v
cd frontend
npm.cmd run build
```

Result after this update: backend 25 tests passed; frontend build passed.

Browser smoke covered:

- Open `/messages`.
- Click `검토 큐로 보내기`.
- See `검토 큐에 추가했습니다.`
- Open `/review`.
- Confirm `메신저 검토 요청` appears in the review queue.

## 2026-05-01 Slack Connector Preparation Update

Added a testable real Slack connector boundary without making live Slack API
calls.

- Connector: `backend/app/connectors/slack.py`
- Test: `backend/tests/test_slack_connector.py`
- Runbook: `docs/superpowers/runbooks/slack-integration.md`
- Environment placeholders added to `.env.example`:
  - `SLACK_BOT_TOKEN`
  - `SLACK_CHANNEL_IDS`
  - `SLACK_WORKSPACE_URL`

The connector maps Slack `conversations.history` message payloads into
ParaWorks `SourceEvent` records and records required history scopes in
`raw_metadata`.

The next Slack step is to implement a real Web API client behind the
`SlackApiClient` protocol with cursor pagination and rate-limit handling.

## 2026-05-02 Source Evidence Review Drawer Update

Aligned with the current root `plan.md` Milestone 3.

- Review API responses now include `source_evidence` rows for each ReviewItem.
- Evidence rows expose source URL, snippet, permission level, confidence,
  rank, importance score, source id, author/timestamp when available, and
  originating AgentRun id.
- `/review` now passes structured evidence into the shared
  `SourceEvidenceDrawer`.
- The Drawer shows reviewer-ready evidence cards and links to the originating
  AgentRun when available.
- The "request more evidence" action now opens a reviewer note field and sends
  the note to the backend before moving the item to `needs_more_evidence`.

Next recommended step from `plan.md`:

1. Add quality and permission regression coverage for Review Queue, RAG, and
   connector evidence.
2. Expand Track A and Track B evidence metadata so more Drawer rows have rank,
   author, timestamp, and source ids.

## 2026-05-02 LangGraph HITL Checkpoint Strategy Update

Aligned with the current root `plan.md` Milestone 4.

- Company Memory orchestration now emits `hitl_checkpoint` from
  `draft_review_candidates`.
- The checkpoint records `checkpoint_type=review_queue`, target ReviewItem ids,
  required statuses, `resume_from_node=retrieve_company_memory`, and
  `resume_policy=resume_after_review_queue_resolution`.
- Orchestration status APIs now expose `hitl_checkpointing`,
  `checkpoint_store=review_queue`, and
  `trusted_knowledge_requires_approval` in the cost/trust policy.

Next recommended step from `plan.md`:

1. Expand Track A and Track B evidence metadata so more Drawer rows have rank,
   author, timestamp, and source ids.
2. Continue connector quality hardening for Slack/Gmail/Drive/Calendar.

## 2026-05-02 Quality And Permission Regression Suite Update

Aligned with the current root `plan.md` Milestone 6.

- Added `backend/tests/test_quality_permission_regression_suite.py`.
- The suite covers source-less review approval rejection, restricted RAG hidden
  match reporting without snippet/citation leakage, HITL checkpoint metadata,
  and cache-hit dedupe for AgentRun/ReviewItem records.
- The suite uses deterministic local fixtures and does not call live Slack,
  Google, LLM, embedding, or external APIs.

Next recommended step from `plan.md`:

1. Continue connector quality hardening for Slack/Gmail/Drive/Calendar.
2. Add connector-specific golden dataset fixtures.

## 2026-05-02 Cross-Agent Evidence Summary Update

Aligned with the current root `plan.md` Track C next-priority cleanup.

- Added `backend/app/agent_runtime/evidence_summary.py`.
- Mail/Document Agent bridge now stores `evidence_summary` in AgentRun metadata.
- Track C Timeline/History/Decision/Todo extraction runs now store
  `evidence_summary` in AgentRun metadata.
- The metadata includes rank, source id, source URL, source type, timestamp,
  author, permission level, importance score, and snippet.

Next recommended step from `plan.md`:

1. Continue connector quality hardening for Slack/Gmail/Drive/Calendar.
2. Add connector-specific golden dataset fixtures.
3. Prepare structured LangChain output adapters behind the deterministic agent
   contracts.

## 2026-05-02 Search Retrieval Backend Alignment Update

Checked `/search` retrieval behavior before continuing connector hardening.

- `/search` page calls both `/api/v1/ask` and `/api/v1/search`.
- `/api/v1/ask` could already use pgvector behind
  `RAG_USE_PGVECTOR_SEARCH=true`, PostgreSQL, and OpenAI embedding key.
- `/api/v1/search` previously always used deterministic lexical ranking.
- Added `backend/app/rag/search_store.py` so both Ask and Search can share the
  pgvector search adapter builder.
- `/api/v1/search` now returns `retrieval_backend` and `cost_policy`.
- The Search UI now shows whether the evidence list used pgvector or the
  default deterministic zero-cost path.

Cost note:

- Default local/demo search still has `embedding_query_call=false`.
- pgvector search requires the feature flag and will make one query embedding
  call when enabled in a PostgreSQL environment with `OPENAI_API_KEY`.

Next recommended step from `plan.md`:

1. Continue connector quality hardening for Slack/Gmail/Drive/Calendar.
2. Add connector-specific golden dataset fixtures.
3. Prepare structured LangChain output adapters behind the deterministic agent
   contracts.

## 2026-05-02 Slack Thread Context Chunking Update

Aligned with the current root `plan.md` Milestone 5.

- Slack connector reply SourceEvents now set body to:
  `Thread parent: <parent text>\nThread reply: <reply text>`.
- Reply metadata now includes `thread_parent_text`, `thread_reply_index`, and
  `thread_context_window=parent_plus_reply`.
- Parent messages remain single-message chunks.
- This improves downstream Review/RAG quality without extra LLM or embedding
  calls.

Next recommended step from `plan.md`:

1. Harden Drive parser/version metadata.
2. Add connector-specific golden dataset fixtures.

## 2026-05-02 Gmail Thread Domain Metadata Update

Aligned with the current root `plan.md` Milestone 5.

- Gmail SourceEvents now parse From, To, and Cc header addresses into
  participants.
- Gmail raw metadata now includes `thread_context_key`, `from_domain`,
  `participant_domains`, `external_domains`, and
  `has_external_participants`.
- This is zero-cost local preprocessing over already fetched Gmail payloads.

Next recommended step from `plan.md`:

1. Harden Drive parser/version metadata.
2. Add connector-specific golden dataset fixtures.
3. Prepare structured LangChain output adapters behind deterministic contracts.

## 2026-05-02 Drive Parser Version Metadata Update

Aligned with the current root `plan.md` Milestone 5.

- Drive files list collection now requests `version` and `headRevisionId`.
- Drive SourceEvents now record `parser_name=google_drive_metadata`,
  `parser_status=metadata_only`,
  `parser_status_reason=content_export_not_enabled`, `document_version`,
  `revision_id`, and `content_signature`.
- This is a low-cost metadata hardening step before full Drive file export and
  parser-specific chunking are added.

Next recommended step from `plan.md`:

1. Harden Calendar connector quality metadata.
2. Add connector-specific golden dataset fixtures.
3. Prepare structured LangChain output adapters behind deterministic contracts.

## 2026-05-02 Calendar Event Quality Metadata Update

Aligned with the current root `plan.md` Milestone 5.

- Calendar SourceEvents now include `event_context_key`, `event_status`,
  `organizer_email`, `creator_email`, `recurring_event_id`,
  `attendee_response_statuses`, `attendee_domains`, `external_domains`,
  `has_external_attendees`, and `duration_minutes`.
- The implementation derives these values locally from already fetched
  Calendar event payloads.
- Milestone 5 connector quality hardening is now complete for Slack, Gmail,
  Drive, and Calendar.

Next recommended step from `plan.md`:

1. Add connector-specific golden dataset fixtures.
2. Add RAG precision/recall smoke metrics.
3. Prepare structured LangChain output adapters behind deterministic contracts.

## 2026-05-02 Connector Golden Dataset Update

Aligned with the current root `plan.md` Milestone 6.

- Added `backend/tests/fixtures/connector_golden_payloads.json` with static
  Slack, Gmail, Drive, and Calendar payloads.
- Added `backend/tests/test_connector_golden_dataset.py`.
- The test verifies agent-ready evidence metadata across connectors:
  Slack thread context, Gmail external-domain flags, Drive parser/version
  signatures, and Calendar RSVP/duration/external-domain metadata.
- The suite is deterministic and makes no live SaaS, LLM, or embedding calls.

Next recommended step from `plan.md`:

1. Add RAG precision/recall smoke metrics.
2. Prepare structured LangChain output adapters behind deterministic contracts.
3. Continue product completion pages after evaluation hooks are stable.

## 2026-05-02 RAG Retrieval Smoke Metrics Update

Aligned with the current root `plan.md` Milestone 6.

- Added `backend/app/rag/evaluation.py`.
- Added `backend/tests/fixtures/rag_smoke_eval_cases.json`.
- Added `backend/tests/test_rag_evaluation_metrics.py`.
- Metrics include precision@k, recall@k, hit rate, expected/retrieved counts,
  and matched expected source ids.
- The smoke fixture runs deterministic retrieval over local seeded chunks and
  confirms expected source ids are recovered.

Cost note:

- This evaluation path uses local fixtures only. It does not call paid LLMs,
  embedding APIs, Slack, or Google.

Next recommended step from `plan.md`:

1. Prepare structured LangChain output adapters behind deterministic contracts.
2. Add product completion pages for decisions/timeline/history.
3. Add production auth plan after product surfaces stabilize.

## 2026-05-02 Structured Memory Extraction Adapter Update

Aligned with the current root `plan.md` Milestone 6.

- Added `backend/app/agents/memory_extraction_agent/langchain_adapter.py`.
- The adapter implements the existing `MemoryExtractionModel` contract and
  returns `MemoryExtractionModelResponse`.
- It uses `chat_model.with_structured_output(StructuredMemoryExtractionOutput)`
  so real LangChain providers can be injected later without changing Track C
  agent contracts.
- Prompt rendering includes bounded evidence rows with source id, source URL,
  timestamp, author, permission level, and text.

Cost note:

- No provider builder or live model call is enabled by default.
- Tests use fake chat models only.
- Evidence rendering is bounded by `max_input_chars`.

Next recommended step from `plan.md`:

1. Add product completion pages for decisions/timeline/history.
2. Add production auth plan after product surfaces stabilize.
3. Keep expanding golden fixtures as new real-data failures appear.

## 2026-05-02 Product Memory Pages Update

Aligned with the current root `plan.md` Milestone 7.

- `/api/v1/knowledge` now includes `timeline_events` and a
  `counts.timeline_events` value.
- `/knowledge` is now an approved company-memory overview.
- Added `/decisions`, `/timeline`, and `/history` pages.
- Added `frontend/src/components/knowledge/MemoryCollection.tsx` for shared
  glass-card memory rendering.
- Extended frontend route inventory and clean-render Playwright coverage for
  the new pages.

Cost note:

- These pages are read-only and do not trigger paid LLM calls, embedding calls,
  provider sync, or reindex jobs.

Next recommended step from `plan.md`:

1. Add production auth plan: httpOnly cookie + refresh token.
2. Add deployment runbook.
3. Consider Notifications/Knowledge Map only after auth/deploy boundaries are
   documented.

## 2026-05-02 Production Auth Plan Update

Aligned with the current root `plan.md` Milestone 7.

- Added `docs/superpowers/runbooks/production-auth.md`.
- The plan moves ParaWorks from demo `X-Demo-User` headers to httpOnly cookie
  sessions with rotating refresh tokens.
- It covers backend auth tables/endpoints, frontend `credentials: "include"`,
  RBAC, source permissions, CSRF, rate limits, audit logs, demo-mode fallback,
  and migration order.

Cost note:

- Auth must not trigger LLM calls, embedding calls, connector sync, or RAG
  reindexing.

Next recommended step from `plan.md`:

1. Add deployment runbook.
2. Then revisit whether Notifications or Knowledge Map are worth building for
   the portfolio demo.

## 2026-05-02 Deployment Runbook Update

Aligned with the current root `plan.md` Milestone 7.

- Added `docs/superpowers/runbooks/deployment.md`.
- The runbook covers Next.js, FastAPI, PostgreSQL + pgvector, Redis, Celery,
  Slack/Google OAuth, environment variables, deployment order, verification,
  cost gates, rollback, monitoring, and production readiness.

Cost note:

- Production verification keeps paid LLM and embedding actions behind explicit
  dry-run or confirmation gates.

Next recommended step from `plan.md`:

1. Add Notifications only if they directly support Review Queue or agent-run
   workflow visibility.
2. Add Knowledge Map only if there is enough time after core product polish.

## 2026-05-02 Notifications Update

Aligned with the current root `plan.md` Milestone 7.

- Added `/api/v1/notifications`.
- The endpoint derives alerts from pending Review Queue items,
  `needs_more_evidence` items, and recent non-complete AgentRuns.
- Added `/notifications` frontend page and sidebar navigation.
- Added Playwright route inventory and render coverage for the page.

Cost note:

- Notifications are read-only database summaries and do not trigger paid LLMs,
  embeddings, provider sync, or RAG reindexing.

Next recommended step from `plan.md`:

1. Add Knowledge Map only if it can be useful without distracting from the core
   Review/RAG story.
2. Otherwise spend the next pass on frontend consistency and final portfolio
   polish.

## 2026-05-03 Knowledge Map Update

Aligned with the current root `plan.md` Milestone 7.

- Added `/api/v1/knowledge/map`.
- The endpoint derives memory nodes from approved Decision, Timeline, History,
  and Todo records, then connects them to source-evidence nodes through stored
  source links.
- Evidence source nodes inherit the strictest connected permission level so the
  map does not make restricted evidence look broadly shareable.
- Added `/knowledge-map`, sidebar navigation, Knowledge Library cross-link, and
  Playwright route inventory coverage.

Cost note:

- Knowledge Map is read-only database aggregation. It does not call LLMs,
  embeddings, connector sync, or reindex jobs.

Next recommended step from `plan.md`:

1. Frontend global consistency and final Liquid Glass polish across all pages.
2. Production auth implementation from `docs/superpowers/runbooks/production-auth.md`.
3. Final demo script and portfolio evidence capture.

## 2026-05-03 Production Auth Cookie Slice

Aligned with the current root `plan.md` Milestone 8.

- Added `AuthUser` and `RefreshToken` models.
- Login now upserts the selected demo account into `auth_users`, stores only a
  hashed refresh token, and sets httpOnly `paraworks_session` and
  `paraworks_refresh` cookies.
- `/api/v1/auth/me` now prefers the signed session cookie over `X-Demo-User`.
- Demo mode still falls back to `X-Demo-User`; production mode rejects requests
  without a valid session cookie.
- Added `/api/v1/auth/refresh` for refresh-token rotation and
  `/api/v1/auth/logout` for refresh-family revocation and cookie clearing.
- Frontend `apiGet`, `apiPost`, and `apiPatch` now send
  `credentials: "include"`.

Cost note:

- Auth remains isolated from paid model, embedding, sync, and reindex paths.

Next recommended step from `plan.md`:

1. Continue frontend global consistency polish where pages still use legacy
   fixed-color alert/card classes.
2. Run final screenshot capture for the portfolio case study.
3. Add Alembic migrations, CSRF, and rate limiting if moving auth closer to
   production deployment.

## 2026-05-03 Portfolio Demo Script Update

Aligned with the current root `plan.md` Milestone 8.

- Added `docs/superpowers/runbooks/portfolio-demo-script.md`.
- The script covers login, integrations, AgentRun observability, Review Queue,
  approved knowledge pages, Knowledge Map, permission-aware RAG, and final
  portfolio close.
- It includes cost and security language for recording or presenting the
  project.

Next recommended step from `plan.md`:

1. Capture final portfolio screenshots or short clips.
2. Add production hardening details that remain outside the current harness:
   Alembic migrations, CSRF, rate limiting, and real identity verification.
3. Keep whole-app Playwright regression green after any frontend polish.

## 2026-05-03 Azure OpenAI-Compatible Alias Update

Aligned with the current root `plan.md` Milestone 8 Azure staging preparation.

- Added `docs/superpowers/specs/2026-05-03-azure-integration-design.md`.
- Added `azure_openai` as a valid Slack LLM provider alias.
- The current alias intentionally uses `OPENAI_API_KEY`,
  `AGENT_LLM_OPENAI_MODEL`, and the existing OpenAI-compatible ChatOpenAI path.
- Added `openai_compatible_embedding_config`, which accepts `azure_openai` but
  still defaults to `https://api.openai.com/v1` for this first key-swap slice.
- Updated `docs/superpowers/runbooks/deployment.md` with Azure Container Apps,
  PostgreSQL pgvector, Redis, Key Vault, Managed Identity, and the alias
  boundary.

Usage:

```text
AGENT_LLM_PROVIDER_ORDER=azure_openai,openai,gemini
OPENAI_API_KEY=<openai-compatible-key>
```

Important:

- This is not yet true Azure OpenAI endpoint/deployment mode. Future work should
  add endpoint, API version, and deployment-name settings behind the same
  `azure_openai` provider name.
- Do not create Azure resources or commit keys without user confirmation on
  budget, region, resource group, and staging domain.

## 2026-05-03 Google Identity and RBAC Update

Aligned with `docs/superpowers/specs/2026-05-03-google-identity-rbac-design.md`.

- Added `docs/superpowers/plans/2026-05-03-google-identity-rbac.md`.
- Google identity login now has a separate login URL and callback path:
  - `GET /api/v1/auth/google/login-url`
  - `GET /api/v1/auth/google/callback`
- Google identity login uses `openid email profile` and `prompt=select_account`.
- Gmail, Drive, and Calendar OAuth remain separate data integration flows.
- Added seeded accounts:
  - `hanvv3@gmail.com`: admin, `public/internal/restricted`
  - `hanvv3@koreacu.ac.kr`: employee, `public/internal`
  - `mina@paraworks.com`: reviewer, `public/internal`
- Added admin user management:
  - `GET /api/v1/admin/users`
  - `PATCH /api/v1/admin/users/{external_id}`
- Admin UI can change role, status, and permission levels, and changes create
  audit logs.
- Review Queue approval is now role-aware:
  - reviewer: `public/internal`
  - manager/admin: `public/internal/restricted`
- Frontend navigation now hides admin/integrations/agent-runs from non-admin
  users and hides Review Queue from users below reviewer.
- Cost and operations APIs are now backend admin-only:
  - `/api/v1/agent-runs`
  - `/api/v1/agent-runs/summary`
  - `/api/v1/agent-runs/{run_id}`
  - `/api/v1/rag/reindex`
  - `/api/v1/rag/reindex/jobs`
  - `/api/v1/rag/reindex/jobs/{job_id}`
  - `/api/v1/rag/indexing/summary`
- Direct AgentRun pages render an admin-required state instead of a 500 when
  the active context cannot access admin observability data.
- Google identity readiness is visible from `/api/v1/auth/google/login-url`
  and `/login`:
  - `redirect_uri`
  - `missing_config`
  - `configured`
- `configured=true` now requires client id, client secret, identity redirect
  URI, and identity state secret.

Environment:

```text
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_IDENTITY_REDIRECT_URI=http://localhost:3000/login/google/callback
GOOGLE_IDENTITY_STATE_SECRET=replace-with-local-google-login-state-secret
```

Cost note:

- Identity login, RBAC checks, admin user management, and Review Queue role
  checks do not call paid LLMs, embeddings, sync jobs, or reindex jobs.

## Portfolio Recording Rule

When future ParaWorks work changes the product story, architecture, UX, testing
evidence, or demo flow, update `docs/portfolio-log.md` in the same session.
Write entries so they can later be reused for a portfolio case study: problem,
implementation, verification evidence, and portfolio angle.

## 2026-05-11 Sidebar Navigation Update

- Sidebar now foregrounds `대시보드`, `프로젝트`, `검토사항`, and `타임라인`.
- Removed Decision, History, and Knowledge Map from the sidebar navigation.
  Their routes still exist for now, but they are no longer primary menu items.
- Added `/projects` as a frontend project workspace with a top project switcher,
  Gantt-style planning, calendar scheduling, board status, and task list views.
- Reworked `/timeline` as a project-scoped timeline. Each timeline item has a
  history summary and a history/Slack icon path that opens the related source
  conversation panel.
- The global top search submits through the left search icon and routes to
  `/search?q=...`, which drives `AI 비서`.
- Navigation and `/search` now label the assistant surface as `AI 비서`.
- `/dashboard` is now a personalized work-home view: today's assigned tasks,
  personal review count, meetings, mentions/updates, assigned projects, and an
  AI 비서 suggestion. Workspace-wide source counts were removed from Dashboard.
- `/dashboard` includes a visible `검토사항` section for assigned review work.
- `/review` is titled `검토사항` and keeps demo fallback review items visible if
  the backend cannot return pending Review Queue data.
- `/timeline` starts full-width and opens the history/source panel only after a
  history icon click; closing the panel returns the timeline to full width.
- `/integrations` now includes the source-by-connector collection status panel,
  since source health and sync volume are connector operations context.
- Verification: `cd frontend && npm run build` passed.

## 2026-05-12 Mail/Document/Calendar Project Grouping Update

- Added `docs/mail-doc-calendar-agent-status.md` as the Developer B status and
  remaining-work document for Google Drive, Gmail, and Calendar project memory.
- Mail/Document Agent evidence packet now includes Calendar chunks in addition
  to Gmail, Gmail attachment, and Drive chunks.
- Calendar event metadata is preserved into the agent evidence packet:
  `event_context_key`, `event_status`, organizer/creator, attendee metadata,
  external domains, and duration.
- Added `GET /api/v1/projects`.
  - Groups Gmail/Drive/Calendar evidence by explicit `project_key`, then
    `scenario`, then URL/title/source-id fallback.
  - Returns project summary, source types, evidence count, strictest permission,
    latest timestamp, and source evidence rows.
  - Hides projects whose strictest permission is outside the current user's
    permission levels and returns `hidden_project_count`.
- Backend test fixtures now attach matching CSRF cookie/header values to unsafe
  requests and clear in-memory auth rate-limit state between tests.
- Verification:

```bash
uv run pytest backend/tests -v
```

Result: 287 passed, 1 skipped.

## 2026-05-12 Local Docker Auth and CSRF Update

- Local production-like Docker mode now seeds auth users and pending Review
  Queue evidence through `backend.app.db.init_db` when `PARAWORKS_ENV=local`.
- `PARAWORKS_DEMO_MODE=false` no longer leaves local email login unusable in
  local development: seeded emails can issue real httpOnly session, refresh,
  and CSRF cookies.
- The login page no longer redirects to `/dashboard` after a failed backend
  login by storing only a local demo account id. AppShell also no longer treats
  localStorage as authenticated state when `/api/v1/auth/me` fails.
- Root cause fixed for the observed symptoms:
  - fake localStorage login made the UI enter the app without backend cookies;
  - unsafe POST routes such as `/api/v1/ask` then failed CSRF validation;
  - admin-only pages saw the user as unauthenticated/non-admin;
  - fresh Docker DBs had no seeded Review Queue items.
- Verification:

```powershell
uv run pytest backend/tests -q
cd frontend
npm.cmd run build
```

Result: backend 289 passed, 1 skipped; frontend build passed.

Direct Docker-backed API check on a secondary backend port confirmed:

- `admin@paraworks.com` and `hanvv3@gmail.com` login return role `admin`;
- `/api/v1/agent-runs` and `/api/v1/admin/users` return 200 for those sessions;
- `/api/v1/review?status=pending_review` returns seeded review items;
- `/api/v1/ask` returns 200 when the `paraworks_csrf` cookie is echoed in
  `X-CSRF-Token`.
