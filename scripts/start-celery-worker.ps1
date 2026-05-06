param(
    [string]$RedisUrl = "redis://localhost:6379/0",
    [string]$DatabaseUrl = "postgresql+psycopg://paraworks:paraworks@localhost:5432/paraworks"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

Write-Host "ParaWorks Celery worker"
Write-Host "Repository: $repoRoot"
Write-Host "Redis:      $RedisUrl"
Write-Host "Database:   $DatabaseUrl"
Write-Host ""

Push-Location $repoRoot
try {
    $env:REDIS_URL = $RedisUrl
    $env:DATABASE_URL = $DatabaseUrl
    $env:CELERY_TASK_ALWAYS_EAGER = 'false'

    uv run celery -A backend.app.tasks.celery_app.celery_app worker --loglevel=info --pool=solo
}
finally {
    Pop-Location
}
