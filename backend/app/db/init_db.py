from sqlalchemy import Engine
from sqlalchemy.orm import Session

import backend.app.models  # noqa: F401
from backend.app.core.config import get_settings
from backend.app.db.base import Base
from backend.app.db.session import engine
from backend.app.ingestion.service import ingest_events
from backend.app.seeds.auth_users import seed_auth_users
from backend.app.seeds.mock_sources import SEED_EVENTS


def init_db(engine_override: Engine | None = None) -> None:
    target_engine = engine_override or engine
    Base.metadata.create_all(bind=target_engine)
    settings = get_settings()
    if settings.paraworks_env == 'local':
        with Session(target_engine) as db:
            seed_auth_users(db)
            db.commit()
            ingest_events(db, SEED_EVENTS)


def main() -> None:
    init_db()
    print('ParaWorks database tables are ready.')


if __name__ == '__main__':
    main()
