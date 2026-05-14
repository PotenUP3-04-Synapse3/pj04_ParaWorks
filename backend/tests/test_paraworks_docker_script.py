from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_paraworks_docker_starts_frontend_after_backend_healthcheck() -> None:
    script = (REPO_ROOT / 'scripts/paraworks-docker.ps1').read_text(encoding='utf-8')

    backend_start = script.index('Write-Step "Starting backend"')
    backend_wait = script.index('Wait-HttpOk -Url "http://$HostAddress`:$BackendPort/health"')
    frontend_start = script.index('Write-Step "Starting frontend"')

    assert backend_start < backend_wait < frontend_start
