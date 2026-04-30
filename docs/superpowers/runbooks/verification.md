# ParaWorks Harness Verification

Run commands from the repository checkout under review. For this branch, the active
worktree is `C:\potenup3\pj04-Paraworks\.worktrees\paraworks-harness`.

## Task 2 Verification

```powershell
docker compose config
```

## Full Harness Verification

Requires the frontend workspace under `frontend/`.

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
