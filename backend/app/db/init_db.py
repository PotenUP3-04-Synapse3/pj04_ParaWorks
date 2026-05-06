from sqlalchemy import Engine

import backend.app.models  # noqa: F401
from backend.app.db.base import Base
from backend.app.db.session import engine


def init_db(engine_override: Engine | None = None) -> None:
    target_engine = engine_override or engine
    Base.metadata.create_all(bind=target_engine)


def main() -> None:
    init_db()
    print('ParaWorks database tables are ready.')


if __name__ == '__main__':
    main()
