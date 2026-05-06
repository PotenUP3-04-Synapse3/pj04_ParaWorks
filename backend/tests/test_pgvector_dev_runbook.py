from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_pgvector_dev_runbook_documents_safe_production_path() -> None:
    runbook = (REPO_ROOT / 'docs/superpowers/runbooks/pgvector-dev.md').read_text(encoding='utf-8')

    assert 'docker compose up -d postgres redis' in runbook
    assert '-SkipApp' in runbook
    assert 'scripts/check_pgvector_dev.py' in runbook
    assert '55432' in runbook
    assert 'OPENAI_API_KEY' in runbook
    assert 'dry_run=false' in runbook
    assert 'Do not commit `.env`' in runbook
    assert 'PARAWORKS_PGVECTOR_TEST_DATABASE_URL' in runbook


def test_pgvector_dev_script_uses_postgres_and_preserves_secret_boundary() -> None:
    script = (REPO_ROOT / 'scripts/start-pgvector-dev.ps1').read_text(encoding='utf-8')

    assert 'docker compose up -d postgres redis' in script
    assert 'DATABASE_URL' in script
    assert 'NoAutoPortFallback' in script
    assert 'check_pgvector_dev.py' in script
    assert 'OPENAI_API_KEY' not in script
    assert 'uv run python -m backend.app.db.init_db' in script


def test_pgvector_dev_checker_documents_schema_expectations() -> None:
    checker = (REPO_ROOT / 'scripts/check_pgvector_dev.py').read_text(encoding='utf-8')

    assert '--ensure-vector-schema' in checker
    assert '--expect-app-schema' in checker
    assert 'pg_extension' in checker
    assert 'rag_vector_documents' in checker
    assert 'vector_index_states' in checker
