# SQLite Smoke Mode Runbook

Use this mode when you want to run the ParaWorks backend and frontend without
Docker, PostgreSQL, Redis, or MinIO. It is intended for quick UI checks,
Playwright smoke tests, and product review sessions.

Run commands from the repository root:

```powershell
C:\Users\hanvv\Study\potenup3\pj04_ParaWorks
```

## One-Command Start

```powershell
.\scripts\start-smoke.ps1
```

The script:

1. Creates `.tmp/paraworks-smoke.db` if needed.
2. Sets `DATABASE_URL=sqlite:///.tmp/paraworks-smoke.db`.
3. Runs `uv run python -m backend.app.db.init_db`.
4. Starts FastAPI on `http://127.0.0.1:8000`.
5. Starts Next.js on `http://127.0.0.1:3000`.

Open:

- Dashboard: `http://127.0.0.1:3000/dashboard`
- Messenger: `http://127.0.0.1:3000/messages`
- Backend health: `http://127.0.0.1:8000/health`

## Manual Start

Backend:

```powershell
$env:DATABASE_URL="sqlite:///.tmp/paraworks-smoke.db"
uv run python -m backend.app.db.init_db
uv run uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Frontend:

```powershell
cd frontend
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

## Reset Smoke Data

Stop the backend, then remove the smoke database:

```powershell
Remove-Item -LiteralPath .tmp\paraworks-smoke.db -Force
```

Run the start command again to recreate the schema.

## What This Mode Does Not Cover

SQLite smoke mode does not verify:

- PostgreSQL-specific behavior.
- pgvector extension availability.
- Redis or Celery queue behavior.
- MinIO object storage behavior.
- Docker Compose configuration.

Use `docs/superpowers/runbooks/local-dev.md` for the full Docker-backed local
runtime.
