#!/usr/bin/env pwsh
<#
.SYNOPSIS
    ParaWorks 개발 서버 실행 스크립트

.EXAMPLE
    .\dev.ps1 backend          # FastAPI 백엔드 서버 (포트 8000)
    .\dev.ps1 frontend         # Next.js 프론트엔드 (포트 3000)
    .\dev.ps1 worker           # Celery 워커
    .\dev.ps1 migrate          # Alembic 마이그레이션 실행
    .\dev.ps1 migrate "메시지"  # 마이그레이션 파일 생성
    .\dev.ps1 lint             # ruff 린트
    .\dev.ps1 fmt              # ruff 포맷
#>

param(
    [Parameter(Position=0)]
    [ValidateSet('backend','frontend','worker','migrate','lint','fmt','help')]
    [string]$Command = 'help',

    [Parameter(Position=1)]
    [string]$Arg = ''
)

$Root = $PSScriptRoot

switch ($Command) {
    'backend' {
        Write-Host "Starting FastAPI backend on http://127.0.0.1:8000 ..." -ForegroundColor Cyan
        Push-Location "$Root\backend"
        uvicorn app.main:app --reload --port 8000
        Pop-Location
    }
    'frontend' {
        Write-Host "Starting Next.js frontend on http://localhost:3000 ..." -ForegroundColor Cyan
        Push-Location "$Root\frontend"
        npm run dev
        Pop-Location
    }
    'worker' {
        Write-Host "Starting Celery worker ..." -ForegroundColor Cyan
        Push-Location "$Root\backend"
        celery -A app.tasks.celery_app worker --loglevel=info
        Pop-Location
    }
    'migrate' {
        Push-Location "$Root\backend"
        if ($Arg) {
            Write-Host "Creating migration: $Arg" -ForegroundColor Yellow
            alembic revision --autogenerate -m $Arg
        } else {
            Write-Host "Running migrations ..." -ForegroundColor Yellow
            alembic upgrade head
        }
        Pop-Location
    }
    'lint' {
        Push-Location "$Root\backend"
        ruff check .
        Pop-Location
    }
    'fmt' {
        Push-Location "$Root\backend"
        ruff format .
        Pop-Location
    }
    default {
        Write-Host ""
        Write-Host "Usage: .\dev.ps1 <command> [arg]" -ForegroundColor White
        Write-Host ""
        Write-Host "Commands:" -ForegroundColor Yellow
        Write-Host "  backend          FastAPI 서버 실행 (포트 8000)" -ForegroundColor Gray
        Write-Host "  frontend         Next.js 서버 실행 (포트 3000)" -ForegroundColor Gray
        Write-Host "  worker           Celery 워커 실행" -ForegroundColor Gray
        Write-Host "  migrate          Alembic 마이그레이션 적용" -ForegroundColor Gray
        Write-Host "  migrate '메시지'  마이그레이션 파일 생성" -ForegroundColor Gray
        Write-Host "  lint             ruff 린트 실행" -ForegroundColor Gray
        Write-Host "  fmt              ruff 포맷 실행" -ForegroundColor Gray
        Write-Host ""
    }
}
