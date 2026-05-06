# Local Development Runbook

Run commands from the repository root.

For quick UI demos without Docker, use
`docs/superpowers/runbooks/sqlite-smoke.md`.

## Start Runtime Services

```powershell
docker compose up -d postgres redis minio
```

## Initialize Demo Database Schema

```powershell
uv run python -m backend.app.db.init_db
```

This creates the local demo application tables in Postgres before the backend
starts.

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
