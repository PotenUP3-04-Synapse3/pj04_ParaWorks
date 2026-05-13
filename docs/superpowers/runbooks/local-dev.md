# Local Development Runbook

Run commands from the repository root.

For quick UI demos without Docker, use
`docs/superpowers/runbooks/sqlite-smoke.md`.

## Start Runtime Services

```powershell
docker compose up -d postgres redis minio
```

## Initialize Database Schema

```powershell
uv run alembic upgrade head
uv run python scripts/check_db_schema.py
```

`alembic upgrade head` applies the tracked schema migrations. The schema check
fails loudly when an existing local database is missing a table or column that a
newer branch expects.

## Seed Local Demo Data

```powershell
uv run python -m backend.app.db.init_db
```

This keeps local seed users and optional demo data available. It still has a
`create_all()` fallback for brand-new local databases, but migrations are the
source of truth for schema changes.

## Start Backend

```powershell
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## Start Frontend

```powershell
cd frontend
npm.cmd run dev -- --hostname 127.0.0.1 --port 3000
```

## Demo Users

- `X-Demo-User: admin` can see `public`, `internal`, and `restricted` sources.
- `X-Demo-User: viewer` can see `public` and `internal` sources.
