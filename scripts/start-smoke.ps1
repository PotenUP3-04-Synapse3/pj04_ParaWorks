param(
    [string]$HostAddress = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [string]$DatabasePath = ".tmp/paraworks-smoke.db"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$databaseFullPath = Join-Path $repoRoot $DatabasePath
$databaseDirectory = Split-Path $databaseFullPath -Parent

if (!(Test-Path $databaseDirectory)) {
    New-Item -ItemType Directory -Path $databaseDirectory | Out-Null
}

$databaseUrl = "sqlite:///$DatabasePath"

Write-Host "ParaWorks smoke mode"
Write-Host "Repository: $repoRoot"
Write-Host "Database:   $databaseUrl"
Write-Host ""

Push-Location $repoRoot
try {
    $env:DATABASE_URL = $databaseUrl
    $env:PARAWORKS_DEMO_MODE = "true"
    uv run python -m backend.app.db.init_db

    $nextDistDir = ".next-smoke"
    $nextCache = Join-Path $repoRoot "frontend/$nextDistDir"
    if (Test-Path $nextCache) {
        Remove-Item -LiteralPath $nextCache -Recurse -Force
    }

    $backendCommand = "`$env:DATABASE_URL='$databaseUrl'; `$env:PARAWORKS_DEMO_MODE='true'; uv run uvicorn backend.app.main:app --host $HostAddress --port $BackendPort"
    $frontendCommand = "`$env:NEXT_DIST_DIR='$nextDistDir'; npm.cmd run dev -- --hostname $HostAddress --port $FrontendPort"

    $backend = Start-Process powershell -WindowStyle Hidden -PassThru -WorkingDirectory $repoRoot -ArgumentList @("-NoProfile", "-Command", $backendCommand)
    $frontend = Start-Process powershell -WindowStyle Hidden -PassThru -WorkingDirectory (Join-Path $repoRoot "frontend") -ArgumentList @("-NoProfile", "-Command", $frontendCommand)

    Write-Host "Backend PID:  $($backend.Id)"
    Write-Host "Frontend PID: $($frontend.Id)"
    Write-Host ""
    Write-Host "Backend:  http://$HostAddress`:$BackendPort/health"
    Write-Host "Frontend: http://$HostAddress`:$FrontendPort/dashboard"
    Write-Host "Messenger: http://$HostAddress`:$FrontendPort/messages"
    Write-Host ""
    Write-Host "Stop with:"
    Write-Host "  Stop-Process -Id $($backend.Id),$($frontend.Id)"
}
finally {
    Pop-Location
}
