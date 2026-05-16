param(
    [string]$HostAddress = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [int]$PostgresPort = 5432,
    [int]$RedisPort = 6379,
    [string]$DatabaseUrl = "",
    [switch]$NoAutoPortFallback,
    [switch]$SkipApp
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")

function Test-HostPortInUse {
    param([int]$Port)
    $connection = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    return $null -ne $connection
}

function Get-AvailableHostPort {
    param(
        [int]$PreferredPort = 5433,
        [int]$MaxPort = 5599
    )
    for ($candidatePort = $PreferredPort; $candidatePort -le $MaxPort; $candidatePort++) {
        if (-not (Test-HostPortInUse -Port $candidatePort)) {
            return $candidatePort
        }
    }

    throw "No available host port found between $PreferredPort and $MaxPort."
}

function Get-ComposePostgresHostPort {
    try {
        $ports = docker ps --filter "name=paraworks-postgres" --format "{{.Ports}}"
        $match = [regex]::Match($ports, "127\.0\.0\.1:(\d+)->5432")
        if ($match.Success) {
            return [int]$match.Groups[1].Value
        }
    }
    catch {
        return 0
    }

    return 0
}

function Test-ComposePostgresOwnsPort {
    param([int]$Port)
    return (Get-ComposePostgresHostPort) -eq $Port
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 30
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            Invoke-RestMethod -Uri $Url -TimeoutSec 2 | Out-Null
            return
        }
        catch {
            Start-Sleep -Seconds 1
        }
    } while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for $Url"
}

if ([string]::IsNullOrWhiteSpace($DatabaseUrl) -and -not $NoAutoPortFallback) {
    if ($PostgresPort -eq 5432 -and (Test-HostPortInUse -Port $PostgresPort) -and -not (Test-ComposePostgresOwnsPort -Port $PostgresPort)) {
        $existingComposePostgresPort = Get-ComposePostgresHostPort
        if ($existingComposePostgresPort -gt 0) {
            Write-Warning "127.0.0.1:5432 is already in use. Reusing Postgres host port $existingComposePostgresPort for ParaWorks."
            $PostgresPort = $existingComposePostgresPort
        }
        else {
            $fallbackPort = Get-AvailableHostPort -PreferredPort 5433
            Write-Warning "127.0.0.1:5432 is already in use. Using Postgres host port $fallbackPort for ParaWorks."
            $PostgresPort = $fallbackPort
        }
    }
}

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
    $DatabaseUrl = "postgresql+psycopg://paraworks:paraworks@127.0.0.1:$PostgresPort/paraworks"
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

    $env:PARAWORKS_DATABASE_URL = $DatabaseUrl
    $env:DATABASE_URL = $DatabaseUrl
    $env:REDIS_URL = "redis://127.0.0.1:$RedisPort/0"
    uv run python scripts/check_pgvector_dev.py --database-url $DatabaseUrl --ensure-vector-schema
    uv run python -m backend.app.db.init_db
    uv run python scripts/check_pgvector_dev.py --database-url $DatabaseUrl --expect-app-schema

    if ($SkipApp) {
        Write-Host "PostgreSQL + pgvector dev database is ready."
        Write-Host "Database URL:"
        Write-Host "  $DatabaseUrl"
        return
    }

    $backendCommand = "`$env:PARAWORKS_DATABASE_URL='$DatabaseUrl'; `$env:DATABASE_URL='$DatabaseUrl'; `$env:REDIS_URL='redis://127.0.0.1:$RedisPort/0'; `$env:PARAWORKS_DEMO_MODE='false'; `$env:PARAWORKS_SEED_DEMO_DATA='false'; uv run uvicorn backend.app.main:app --host $HostAddress --port $BackendPort"
    $frontendCommand = "npm.cmd run dev -- --hostname localhost --port $FrontendPort"

    $backend = Start-Process powershell -WindowStyle Hidden -PassThru -WorkingDirectory $repoRoot -ArgumentList @("-NoProfile", "-Command", $backendCommand)
    $frontend = Start-Process powershell -WindowStyle Hidden -PassThru -WorkingDirectory (Join-Path $repoRoot "frontend") -ArgumentList @("-NoProfile", "-Command", $frontendCommand)
    Wait-HttpOk -Url "http://$HostAddress`:$BackendPort/health" -TimeoutSeconds 45

    Write-Host "Backend PID:  $($backend.Id)"
    Write-Host "Frontend PID: $($frontend.Id)"
    Write-Host ""
    Write-Host "Backend:  http://$HostAddress`:$BackendPort/health"
    Write-Host "Frontend: http://localhost`:$FrontendPort/dashboard"
    Write-Host ""
    Write-Host "Stop with:"
    Write-Host "  Stop-Process -Id $($backend.Id),$($frontend.Id)"
}
finally {
    Pop-Location
}
