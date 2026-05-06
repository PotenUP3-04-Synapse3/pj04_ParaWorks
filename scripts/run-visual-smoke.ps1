param(
    [string]$HostAddress = "127.0.0.1",
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [string]$DatabasePath = ".tmp/paraworks-visual-smoke.db"
)

$ErrorActionPreference = "Stop"

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$startedPids = @()

function Test-PortOpen {
    param([string]$HostName, [int]$Port)

    $client = [System.Net.Sockets.TcpClient]::new()
    try {
        $result = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $result.AsyncWaitHandle.WaitOne(500)) {
            return $false
        }
        $client.EndConnect($result)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Dispose()
    }
}

function Wait-ForHealth {
    param([string]$Url)

    for ($i = 0; $i -lt 40; $i++) {
        try {
            $health = Invoke-RestMethod $Url
            if ($health.status -eq "ok") {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "Backend health check did not become ready: $Url"
}

function Wait-ForFrontend {
    param([string]$Url)

    for ($i = 0; $i -lt 40; $i++) {
        try {
            $response = Invoke-WebRequest $Url -UseBasicParsing
            if ($response.StatusCode -eq 200) {
                return
            }
        }
        catch {
            Start-Sleep -Milliseconds 500
        }
    }
    throw "Frontend did not become ready: $Url"
}

$backendUrl = "http://$HostAddress`:$BackendPort"
$frontendUrl = "http://$HostAddress`:$FrontendPort"

Push-Location $repoRoot
try {
    $backendOpen = Test-PortOpen -HostName $HostAddress -Port $BackendPort
    $frontendOpen = Test-PortOpen -HostName $HostAddress -Port $FrontendPort

    if ($backendOpen -and $frontendOpen) {
        Write-Host "Using existing smoke servers at $backendUrl and $frontendUrl"
    }
    elseif ($backendOpen -or $frontendOpen) {
        throw "Only one smoke port is open. Stop the partial server or choose different ports."
    }
    else {
        $output = .\scripts\start-smoke.ps1 -HostAddress $HostAddress -BackendPort $BackendPort -FrontendPort $FrontendPort -DatabasePath $DatabasePath
        $output | ForEach-Object { Write-Host $_ }
        foreach ($line in $output) {
            if ($line -match "Backend PID:\s+(\d+)") {
                $startedPids += [int]$Matches[1]
            }
            if ($line -match "Frontend PID:\s+(\d+)") {
                $startedPids += [int]$Matches[1]
            }
        }
    }

    Wait-ForHealth "$backendUrl/health"
    Wait-ForFrontend "$frontendUrl/dashboard"

    Invoke-RestMethod -Method Post "$backendUrl/api/v1/integrations/slack/sync" | Out-Null
    Invoke-RestMethod -Method Post "$backendUrl/api/v1/integrations/gmail/sync" | Out-Null
    Invoke-RestMethod -Method Post "$backendUrl/api/v1/rag/reindex/jobs" | Out-Null

    Push-Location (Join-Path $repoRoot "frontend")
    try {
        $env:PLAYWRIGHT_BASE_URL = $frontendUrl
        $env:PLAYWRIGHT_API_BASE_URL = $backendUrl
        npm.cmd run test:visual
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($startedPids.Count -gt 0) {
        Stop-Process -Id $startedPids -Force -ErrorAction SilentlyContinue
    }
    Pop-Location
}
