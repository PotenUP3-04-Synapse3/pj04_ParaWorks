from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import backend.app.models  # noqa: F401
from backend.app.core.rate_limit import _LIMITER_STORAGE
from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import create_app


@pytest.fixture(autouse=True)
def clear_rate_limiter() -> Generator[None, None, None]:
    _LIMITER_STORAGE.clear()
    yield
    _LIMITER_STORAGE.clear()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine(
        'sqlite://',
        connect_args={'check_same_thread': False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_local = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    db = session_local()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session: Session) -> Generator[TestClient, None, None]:
    app = create_app()

    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        test_client.cookies.set('paraworks_csrf', 'test-csrf-token', domain='testserver.local', path='/')
        original_request = test_client.request

        def csrf_cookie_token() -> str | None:
            fallback = None
            for cookie in test_client.cookies.jar:
                if cookie.name != 'paraworks_csrf':
                    continue
                fallback = cookie.value
                if cookie.domain == 'testserver.local':
                    return cookie.value
            return fallback

        def request_with_csrf(method: str, url, *args, **kwargs):
            headers = dict(kwargs.pop('headers', {}) or {})
            token = csrf_cookie_token()
            if method.upper() not in ('GET', 'HEAD', 'OPTIONS', 'TRACE') and token:
                headers.setdefault('X-CSRF-Token', token)
            return original_request(method, url, *args, headers=headers, **kwargs)

        test_client.request = request_with_csrf
        yield test_client
    app.dependency_overrides.clear()
