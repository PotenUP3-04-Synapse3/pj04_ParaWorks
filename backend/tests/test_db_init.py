from sqlalchemy import create_engine, inspect

from backend.app.db.init_db import init_db


def test_init_db_creates_expected_tables_on_fresh_engine() -> None:
    engine = create_engine('sqlite:///:memory:')

    init_db(engine_override=engine)

    tables = set(inspect(engine).get_table_names())
    assert {'sources', 'review_items', 'sync_jobs', 'agent_runs'} <= tables
