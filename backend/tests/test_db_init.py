from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from backend.app.core.config import get_settings
from backend.app.db.init_db import init_db
from backend.app.models import AuthUser, ReviewItem


def test_init_db_creates_expected_tables_on_fresh_engine() -> None:
    engine = create_engine('sqlite:///:memory:')

    init_db(engine_override=engine)

    tables = set(inspect(engine).get_table_names())
    assert {'sources', 'review_items', 'sync_jobs', 'agent_runs', 'vector_index_states'} <= tables


def test_init_db_seeds_local_docker_users_and_review_items(monkeypatch) -> None:
    monkeypatch.setenv('PARAWORKS_ENV', 'local')
    get_settings.cache_clear()
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )

    try:
        init_db(engine_override=engine)

        with Session(engine) as db:
            users_by_email = {user.email: user for user in db.query(AuthUser).all()}
            assert users_by_email['admin@paraworks.com'].role == 'admin'
            assert users_by_email['hanvv3@gmail.com'].role == 'admin'
            assert db.query(ReviewItem).filter(ReviewItem.status == 'pending_review').count() >= 1
    finally:
        get_settings.cache_clear()
