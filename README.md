# ParaWorks

ParaWorks is a Korean-first, multi-agent company memory platform. It preserves
source evidence, human review status, permissions, and cost metadata before AI
output becomes trusted company knowledge.

The current local default is a Docker-backed, production-like development mode.
SQLite smoke mode still exists for quick UI checks, but it is not the main
server startup path.

## Start The Full Local Stack

Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\paraworks-docker.ps1
```

If your PowerShell policy already allows local scripts, this shorter form also
works:

```powershell
.\scripts\paraworks-docker.ps1
```

The helper does the full local startup sequence:

1. Starts Docker Desktop when available and waits for the Docker daemon.
2. Runs Docker Compose services for PostgreSQL + pgvector, Redis, and MinIO.
3. Waits for Postgres, checks pgvector, applies Alembic migrations, verifies the
   application schema, and seeds local application data.
4. Starts the FastAPI backend locally.
5. Starts the Next.js frontend locally after backend `/health` is ready.

Open:

- Frontend login: `http://127.0.0.1:3000/login`
- Backend health: `http://127.0.0.1:8000/health`
- MinIO console: `http://127.0.0.1:9001`

Important: FastAPI and Next.js are local dev processes, not app containers.
Docker supplies the production-like infrastructure services and pgvector-backed
database path.

## Stop The Stack

```powershell
.\scripts\paraworks-docker.ps1 -Stop
```

To stop the app processes and run `docker compose down` instead of only stopping
the Compose services:

```powershell
.\scripts\paraworks-docker.ps1 -Down
```

## Ports And Conflict Handling

Default local ports:

- Frontend: `127.0.0.1:3000`
- Backend: `127.0.0.1:8000`
- Postgres: `127.0.0.1:5432`
- Redis: `127.0.0.1:6379`
- MinIO API and console: `127.0.0.1:9000`, `127.0.0.1:9001`

If `127.0.0.1:5432` is already used by a non-ParaWorks process, the PowerShell
helper reuses an existing ParaWorks Postgres container port when one is already
running. Otherwise it falls back to the next available host port starting at
`5433` and prints the matching `DATABASE_URL`.

Backend and frontend ports must be free. Use explicit ports when needed:

```powershell
.\scripts\paraworks-docker.ps1 -BackendPort 8001 -FrontendPort 3001
```

Use alternate infrastructure ports when you want to choose them yourself:

```powershell
.\scripts\paraworks-docker.ps1 -PostgresPort 5433 -RedisPort 56379
```

## Database-Only Mode

To prepare Docker services, schema, migrations, seed data, and pgvector checks
without starting FastAPI or Next.js:

```powershell
.\scripts\paraworks-docker.ps1 -SkipApp
```

For focused pgvector development, the older helper is still available:

```powershell
.\scripts\start-pgvector-dev.ps1 -SkipApp
```

See `docs/superpowers/runbooks/pgvector-dev.md` for fake embedding integration
tests, live embedding guardrails, and Celery/Redis queue checks.

## Fast Smoke Mode

When Docker is unavailable and you only need a quick UI/product smoke run:

```powershell
.\scripts\start-smoke.ps1
```

This uses a local SQLite database and does not validate PostgreSQL, pgvector,
Redis, MinIO, or Docker Compose behavior. See
`docs/superpowers/runbooks/sqlite-smoke.md` for details.

## Environment And Secrets

Copy `.env.example` to `.env` only when you need local provider, OAuth, or port
settings.

Never commit `.env`, provider API keys, OAuth tokens, Slack tokens, refresh
tokens, or other secrets.

Live LLM and embedding provider calls require local secrets and explicit user
actions. Automated tests and deterministic smoke paths must not call live
providers.

## Verification References

- Current product direction: `plan.md`
- Agent collaboration rules: `AGENTS.md`
- Full Docker-backed local runbook: `docs/superpowers/runbooks/local-dev.md`
- pgvector runbook: `docs/superpowers/runbooks/pgvector-dev.md`
- SQLite smoke runbook: `docs/superpowers/runbooks/sqlite-smoke.md`

Useful static checks:

```powershell
docker compose config
uv run pytest backend/tests/test_paraworks_docker_script.py backend/tests/test_pgvector_dev_runbook.py -q
```
