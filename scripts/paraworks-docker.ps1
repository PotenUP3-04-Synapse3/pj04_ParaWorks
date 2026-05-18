param(
    [switch]$Stop,
    [switch]$Down,
    [switch]$SkipApp,
    [switch]$NoDockerDesktopLaunch,
    [string]$HostAddress = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [int]$PostgresPort = 5432,
    [int]$RedisPort = 6379,
    [string]$DatabaseUrl = ""
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$tmpDir = Join-Path $repoRoot ".tmp"
$statePath = Join-Path $tmpDir "paraworks-docker-state.json"

function Write-Step {
    param([string]$Message)
    Write-Host "[ParaWorks] $Message"
}

function Invoke-Checked {
    param(
        [scriptblock]$Command,
        [string]$ErrorMessage
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw $ErrorMessage
    }
}

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

function Get-ListeningProcessIds {
    param([int[]]$Ports)
    return @(
        Get-NetTCPConnection -LocalPort $Ports -State Listen -ErrorAction SilentlyContinue |
        Select-Object -ExpandProperty OwningProcess -Unique
    )
}

function Stop-ProcessIds {
    param([int[]]$ProcessIds)
    foreach ($processId in @($ProcessIds | Where-Object { $_ -gt 0 } | Select-Object -Unique)) {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($null -ne $process) {
            Write-Step "Stopping $($process.ProcessName) pid=$processId"
            Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        }
    }
}

function Test-ComposePostgresOwnsPort {
    param([int]$Port)
    return (Get-ComposePostgresHostPort) -eq $Port
}

function Start-DockerDesktop {
    if ($NoDockerDesktopLaunch) {
        return
    }

    $dockerDesktopPath = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if ((Test-Path -LiteralPath $dockerDesktopPath) -and -not (Get-Process -Name "Docker Desktop" -ErrorAction SilentlyContinue)) {
        Write-Step "Starting Docker Desktop"
        Start-Process -FilePath $dockerDesktopPath -WindowStyle Hidden
    }
}

function Wait-DockerReady {
    param([int]$TimeoutSeconds = 180)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        docker version *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 5
    } while ((Get-Date) -lt $deadline)

    throw "Docker daemon did not become ready within $TimeoutSeconds seconds. Open Docker Desktop and try again."
}

function Wait-PostgresReady {
    param([int]$TimeoutSeconds = 60)
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        docker exec paraworks-postgres pg_isready -U paraworks -d paraworks *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 1
    } while ((Get-Date) -lt $deadline)

    throw "Postgres did not become ready within $TimeoutSeconds seconds."
}

function Wait-HttpOk {
    param(
        [string]$Url,
        [int]$TimeoutSeconds = 45
    )
    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    do {
        try {
            Invoke-WebRequest -UseBasicParsing -Uri $Url -TimeoutSec 3 | Out-Null
            return
        }
        catch {
            Start-Sleep -Seconds 1
        }
    } while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for $Url"
}

function Read-State {
    if (-not (Test-Path -LiteralPath $statePath)) {
        return $null
    }
    return Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json
}

function Stop-Paraworks {
    $state = Read-State
    $ports = @($BackendPort, $FrontendPort)
    $stateProcessIds = @()

    if ($null -ne $state) {
        $ports = @($state.backend_port, $state.frontend_port) | Where-Object { $_ -gt 0 }
        $stateProcessIds = @($state.backend_pid, $state.frontend_pid) | Where-Object { $_ -gt 0 }
    }

    Write-Step "Stopping backend/frontend processes"
    Stop-ProcessIds -ProcessIds $stateProcessIds

    $portProcessIds = Get-ListeningProcessIds -Ports $ports
    Stop-ProcessIds -ProcessIds $portProcessIds

    Push-Location $repoRoot
    try {
        Wait-DockerReady -TimeoutSeconds 15
        if ($Down) {
            Write-Step "Running docker compose down"
            docker compose down
        }
        else {
            Write-Step "Stopping docker compose services"
            docker compose stop postgres redis minio
        }
    }
    catch {
        Write-Warning "Docker stop skipped or failed: $($_.Exception.Message)"
    }
    finally {
        Pop-Location
    }

    if (Test-Path -LiteralPath $statePath) {
        Remove-Item -LiteralPath $statePath -Force
    }

    Write-Step "Stopped"
}

if ($Stop -or $Down) {
    Stop-Paraworks
    return
}

New-Item -ItemType Directory -Force -Path $tmpDir | Out-Null

$existingState = Read-State
if ($null -ne $existingState) {
    $existingBackendPort = [int]$existingState.backend_port
    $existingFrontendPort = [int]$existingState.frontend_port
    if ((Test-HostPortInUse -Port $existingBackendPort) -and (Test-HostPortInUse -Port $existingFrontendPort)) {
        Write-Step "Already running"
        Write-Host "Backend:  http://$HostAddress`:$existingBackendPort/health"
        Write-Host "Frontend: http://127.0.0.1:$existingFrontendPort/login"
        Write-Host ""
        Write-Host "Stop with:"
        Write-Host "  .\scripts\paraworks-docker.ps1 -Stop"
        return
    }
}

Start-DockerDesktop
Wait-DockerReady

if ([string]::IsNullOrWhiteSpace($DatabaseUrl)) {
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
    $DatabaseUrl = "postgresql+psycopg://paraworks:paraworks@127.0.0.1:$PostgresPort/paraworks"
}

if (Test-HostPortInUse -Port $BackendPort) {
    throw "Backend port $BackendPort is already in use. Run .\scripts\paraworks-docker.ps1 -Stop first, or choose -BackendPort."
}
if (Test-HostPortInUse -Port $FrontendPort) {
    throw "Frontend port $FrontendPort is already in use. Run .\scripts\paraworks-docker.ps1 -Stop first, or choose -FrontendPort."
}

Write-Step "Starting production-like Docker dev mode"
Write-Host "Repository: $repoRoot"
Write-Host "Database:   $DatabaseUrl"
Write-Host "Postgres:   127.0.0.1:$PostgresPort -> container 5432"
Write-Host "Redis:      127.0.0.1:$RedisPort -> container 6379"
Write-Host "Backend:    http://$HostAddress`:$BackendPort"
Write-Host "Frontend:   http://127.0.0.1:$FrontendPort"
Write-Host "Demo mode:  false"
Write-Host ""

Push-Location $repoRoot
try {
    $env:PARAWORKS_POSTGRES_PORT = "$PostgresPort"
    $env:PARAWORKS_REDIS_PORT = "$RedisPort"

    Write-Step "Starting Docker services"
    Invoke-Checked -ErrorMessage "Docker compose services failed to start." -Command {
        docker compose up -d postgres redis minio
    }

    Write-Step "Waiting for Postgres"
    Wait-PostgresReady -TimeoutSeconds 60

    $env:PARAWORKS_DATABASE_URL = $DatabaseUrl
    $env:DATABASE_URL = $DatabaseUrl
    $env:REDIS_URL = "redis://127.0.0.1:$RedisPort/0"
    $env:PARAWORKS_DEMO_MODE = "false"

    Write-Step "Checking pgvector schema"
    Invoke-Checked -ErrorMessage "pgvector schema check failed." -Command {
        uv run python scripts/check_pgvector_dev.py --database-url $DatabaseUrl --ensure-vector-schema
    }

    Write-Step "Applying database migrations"
    Invoke-Checked -ErrorMessage "Alembic migrations failed." -Command {
        uv run alembic upgrade head
    }

    Write-Step "Checking application schema"
    Invoke-Checked -ErrorMessage "Application schema check failed." -Command {
        uv run python scripts/check_db_schema.py --database-url $DatabaseUrl
    }

    Write-Step "Seeding local application data"
    Invoke-Checked -ErrorMessage "Application data seed failed." -Command {
        uv run python -m backend.app.db.init_db
    }

    Write-Step "Checking final database schema"
    Invoke-Checked -ErrorMessage "Final application schema check failed." -Command {
        uv run python scripts/check_db_schema.py --database-url $DatabaseUrl
    }

    Write-Step "Checking pgvector runtime status"
    Invoke-Checked -ErrorMessage "pgvector runtime status check failed." -Command {
        uv run python scripts/check_pgvector_dev.py --database-url $DatabaseUrl --expect-app-schema
    }

    if ($SkipApp) {
        Write-Step "Docker database services are ready"
        return
    }

    $backendOut = Join-Path $tmpDir "paraworks-backend.out.log"
    $backendErr = Join-Path $tmpDir "paraworks-backend.err.log"
    $frontendOut = Join-Path $tmpDir "paraworks-frontend.out.log"
    $frontendErr = Join-Path $tmpDir "paraworks-frontend.err.log"

    $backendCommand = @"
`$env:PARAWORKS_DATABASE_URL = '$DatabaseUrl'
`$env:DATABASE_URL = '$DatabaseUrl'
`$env:REDIS_URL = 'redis://127.0.0.1:$RedisPort/0'
`$env:PARAWORKS_DEMO_MODE = 'false'
`$env:AGENT_LLM_ENABLED = 'true'
uv run uvicorn backend.app.main:app --host $HostAddress --port $BackendPort
"@

    $frontendCommand = @"
`$env:NEXT_PUBLIC_API_BASE_URL = 'http://$HostAddress`:$BackendPort'
npm.cmd run dev -- --hostname 127.0.0.1 --port $FrontendPort
"@

    Write-Step "Starting backend"
    $backend = Start-Process powershell -WindowStyle Hidden -PassThru -WorkingDirectory $repoRoot -RedirectStandardOutput $backendOut -RedirectStandardError $backendErr -ArgumentList @("-NoProfile", "-Command", $backendCommand)

    Wait-HttpOk -Url "http://$HostAddress`:$BackendPort/health" -TimeoutSeconds 60

    Write-Step "Starting frontend"
    $frontend = Start-Process powershell -WindowStyle Hidden -PassThru -WorkingDirectory (Join-Path $repoRoot "frontend") -RedirectStandardOutput $frontendOut -RedirectStandardError $frontendErr -ArgumentList @("-NoProfile", "-Command", $frontendCommand)

    Wait-HttpOk -Url "http://127.0.0.1:$FrontendPort/login" -TimeoutSeconds 90

    $state = [ordered]@{
        backend_pid   = $backend.Id
        frontend_pid  = $frontend.Id
        backend_port  = $BackendPort
        frontend_port = $FrontendPort
        postgres_port = $PostgresPort
        redis_port    = $RedisPort
        database_url  = $DatabaseUrl
        started_at    = (Get-Date).ToString("o")
    }
    $state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8

    Write-Host ""
    Write-Step "Ready"
    Write-Host "Backend PID:  $($backend.Id)"
    Write-Host "Frontend PID: $($frontend.Id)"
    Write-Host "Backend:      http://$HostAddress`:$BackendPort/health"
    Write-Host "Frontend:     http://127.0.0.1:$FrontendPort/login"
    Write-Host "Logs:"
    Write-Host "  $backendErr"
    Write-Host "  $frontendErr"
    Write-Host ""
    Write-Host "Stop with:"
    Write-Host "  .\scripts\paraworks-docker.ps1 -Stop"
}
finally {
    Pop-Location
}
