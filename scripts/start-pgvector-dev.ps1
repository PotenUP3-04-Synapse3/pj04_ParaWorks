param(
    [string]$HostAddress = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [int]$PostgresPort = 5432,
    [int]$RedisPort = 6379,
    [string]$DatabaseUrl = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    $DatabaseUrl = "postgresql+psycopg://paraworks:paraworks@localhost:$PostgresPort/paraworks"
}

Write-Host "ParaWorks pgvector dev mode"
Write-Host "Repository: $repoRoot"
Write-Host "Database:   $DatabaseUrl"
Write-Host "Postgres:   127.0.0.1:$PostgresPort -> container 5432"
Write-Host "Redis:      127.0.0.1:$RedisPort -> container 6379"
Write-Host ""

Push-Location $repoRoot
try {
    $env:PARAWORKS_POSTGRES_PORT = "$PostgresPort"
    $env:PARAWORKS_REDIS_PORT = "$RedisPort"
    docker compose up -d postgres redis

    $env:DATABASE_URL = $DatabaseUrl
    uv run python -m backend.app.db.init_db

    $backendCommand = "`$env:DATABASE_URL='$DatabaseUrl'; `$env:PARAWORKS_DEMO_MODE='true'; uv run uvicorn backend.app.main:app --host $HostAddress --port $BackendPort"
    $frontendCommand = "npm.cmd run dev -- --hostname $HostAddress --port $FrontendPort"

    $backend = Start-Process powershell -WindowStyle Hidden -PassThru -WorkingDirectory $repoRoot -ArgumentList @("-NoProfile", "-Command", $backendCommand)
    $frontend = Start-Process powershell -WindowStyle Hidden -PassThru -WorkingDirectory (Join-Path $repoRoot "frontend") -ArgumentList @("-NoProfile", "-Command", $frontendCommand)

    Write-Host "Backend PID:  $($backend.Id)"
    Write-Host "Frontend PID: $($frontend.Id)"
    Write-Host ""
    Write-Host "Backend:  http://$HostAddress`:$BackendPort/health"
    Write-Host "Frontend: http://$HostAddress`:$FrontendPort/dashboard"
    Write-Host ""
    Write-Host "Stop with:"
    Write-Host "  Stop-Process -Id $($backend.Id),$($frontend.Id)"
}
finally {
    Pop-Location
}
