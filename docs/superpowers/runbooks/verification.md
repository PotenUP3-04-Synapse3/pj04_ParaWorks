# ParaWorks Harness Verification

Run commands from `C:\potenup3\pj04-Paraworks`.

## Task 2 Verification

```powershell
docker compose config
```

## Full-Harness Verification

Run this after Task 6 creates `frontend/package.json`.

```powershell
uv run pytest backend/tests -v
cd frontend
npm.cmd run build
```
