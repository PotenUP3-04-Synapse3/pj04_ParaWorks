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


def test_paraworks_docker_waits_for_postgres_before_schema_checks() -> None:
    script = (REPO_ROOT / 'scripts/paraworks-docker.ps1').read_text(encoding='utf-8')

    compose_up = script.index('docker compose up -d postgres redis minio')
    wait_postgres = script.index('Wait-PostgresReady -TimeoutSeconds 60')
    pgvector_check = script.index('scripts/check_pgvector_dev.py --database-url $DatabaseUrl --ensure-vector-schema')

    assert compose_up < wait_postgres < pgvector_check


def test_paraworks_docker_wraps_native_commands_with_exit_code_checks() -> None:
    script = (REPO_ROOT / 'scripts/paraworks-docker.ps1').read_text(encoding='utf-8')

    assert 'function Invoke-Checked' in script
    assert 'if ($LASTEXITCODE -ne 0)' in script
    assert 'Invoke-Checked -ErrorMessage "Alembic migrations failed."' in script
