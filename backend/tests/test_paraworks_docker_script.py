from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_paraworks_docker_starts_frontend_after_backend_healthcheck() -> None:
    script = (REPO_ROOT / 'scripts/paraworks-docker.ps1').read_text(encoding='utf-8')

    backend_start = script.index('Write-Step "Starting backend"')
    backend_wait = script.index('Wait-HttpOk -Url "http://$HostAddress`:$BackendPort/health"')
    frontend_start = script.index('Write-Step "Starting frontend"')

    assert backend_start < backend_wait < frontend_start


def test_paraworks_docker_is_idempotent_when_state_file_exists() -> None:
    script = (REPO_ROOT / 'scripts/paraworks-docker.ps1').read_text(encoding='utf-8')

    state_check = script.index('$existingState = Read-State')
    already_running = script.index('Already running')
    backend_port_throw = script.index('Backend port $BackendPort is already in use')

    assert state_check < already_running < backend_port_throw
