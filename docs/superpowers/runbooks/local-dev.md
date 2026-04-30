# Local Development Runbook

Run commands from `C:\potenup3\pj04-Paraworks`.

## Start Runtime Services

```powershell
docker compose up -d postgres redis minio
```

## Start Backend

```powershell
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## Start Frontend

```powershell
cd frontend
npm run dev
```

## Demo Users

- `X-Demo-User: admin` can see `public`, `internal`, and `restricted` sources.
- `X-Demo-User: viewer` can see `public` and `internal` sources.
