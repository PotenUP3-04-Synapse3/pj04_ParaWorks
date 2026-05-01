# ParaWorks Harness Session Handoff

Updated: 2026-05-01

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

## Portfolio Recording Rule

When future ParaWorks work changes the product story, architecture, UX, testing
evidence, or demo flow, update `docs/portfolio-log.md` in the same session.
Write entries so they can later be reused for a portfolio case study: problem,
implementation, verification evidence, and portfolio angle.
