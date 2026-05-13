from pathlib import Path

from sqlalchemy import create_engine

from backend.app.db.base import Base
from scripts.check_db_schema import check_schema


def test_alembic_operational_files_exist() -> None:
    assert Path('alembic.ini').is_file()
    assert Path('backend/migrations/env.py').is_file()
    assert Path('backend/migrations/script.py.mako').is_file()
    assert Path('backend/migrations/versions/0001_create_current_schema.py').is_file()


def test_schema_checker_reports_missing_model_tables() -> None:
    engine = create_engine('sqlite:///:memory:')

    result = check_schema(engine, include_native_pgvector=False)

    assert not result.ok
    assert 'auth_users' in result.missing_tables
    assert 'assistant_conversations' in result.missing_tables


def test_schema_checker_accepts_sqlalchemy_metadata_tables() -> None:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(bind=engine)

    result = check_schema(engine, include_native_pgvector=False)

    assert result.ok
    assert result.missing_tables == []
    assert result.missing_columns == {}
