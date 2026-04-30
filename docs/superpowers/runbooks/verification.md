# ParaWorks Harness Verification

Run commands from `C:\potenup3\pj04-Paraworks`.

## Task 2 Verification

```powershell
docker compose config
```

## Full Harness Verification

Run this after Task 6 creates `frontend/package.json`.

```powershell
docker compose config
uv run pytest backend/tests -v
cd frontend
npm.cmd run build
```

Expected backend checks:

- health endpoint returns demo mode
- mock connectors expose source evidence
- sync creates pending review items
- approve/reject transitions work
- viewer cannot see restricted source content
- admin can see restricted source content
- SSE job status emits progress and done events

Expected frontend check:

- dashboard, integrations, review, and search routes compile
