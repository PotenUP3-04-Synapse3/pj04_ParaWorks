# ParaWorks Harness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first ParaWorks service harness: local FastAPI/Next.js runtime, mock connector demo flow, review/search workflow, permission guard, SSE job status, and verification runbooks.

**Architecture:** Use an Adapter-First Demo Harness. FastAPI owns API routes, ingestion, deterministic extraction, permission checks, and job status; Next.js owns dashboard, integrations, review, and search screens; PostgreSQL with pgvector, Redis, and MinIO run through Docker Compose.

**Tech Stack:** Python 3.12, uv, FastAPI, Pydantic v2, SQLAlchemy 2, Alembic, PostgreSQL with pgvector, Redis, Celery, MinIO, pytest, httpx, Next.js 15, TypeScript, Tailwind CSS, TanStack Query, Zustand, Zod, lucide-react.

---

## Repository

Root: `C:\potenup3\pj04-Paraworks`

Spec: `docs/superpowers/specs/2026-04-30-paraworks-harness-design.md`

## File Structure

- Modify: `pyproject.toml` - focused backend harness dependencies.
- Modify: `README.md` - first harness overview.
- Create: `.env.example` - local config.
- Create: `docker-compose.yml` - Postgres/pgvector, Redis, MinIO.
- Create: `docker/postgres/init/001_extensions.sql` - pgvector extension.
- Create: `backend/app/main.py` - FastAPI app.
- Create: `backend/app/core/config.py` - settings.
- Create: `backend/app/core/demo_auth.py` - demo user boundary.
- Create: `backend/app/db/base.py` and `backend/app/db/session.py` - SQLAlchemy setup.
- Create: `backend/app/models/*.py` - source, review, job, knowledge models.
- Create: `backend/app/connectors/*.py` - connector contract and mock connectors.
- Create: `backend/app/seeds/mock_sources.py` - deterministic seed scenarios.
- Create: `backend/app/ingestion/service.py` - event normalization.
- Create: `backend/app/knowledge/extractor.py` - deterministic review candidates.
- Create: `backend/app/permissions/service.py` - permission checks.
- Create: `backend/app/api/v1/*.py` - dashboard, integrations, review, search, stream routes.
- Create: `backend/tests/*.py` - contract, pipeline, permission, review, stream tests.
- Create: `frontend/*` and `frontend/src/**/*` - Next.js demo UI.
- Create: `docs/superpowers/decisions/ADR-0001-adapter-first-demo-harness.md`.
- Create: `docs/superpowers/runbooks/local-dev.md`, `demo-seed.md`, `verification.md`.

---

### Task 1: Phase 0 Cleanup and Health Baseline

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Create: `backend/__init__.py`
- Create: `backend/app/__init__.py`
- Create: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Write the failing health test**

Create `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {'status': 'ok', 'service': 'paraworks'}
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
uv run pytest backend/tests/test_health.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.app'`.

- [ ] **Step 3: Replace dependencies in `pyproject.toml`**

Use this focused dependency set and keep existing `tool.ruff` and `tool.mypy` sections:

```toml
[project]
name = "pj04-paraworks"
version = "0.1.0"
description = "ParaWorks service harness"
readme = "README.md"
requires-python = ">=3.12"
dependencies = [
    "alembic>=1.17.2",
    "celery>=5.6.0",
    "fastapi>=0.133.0",
    "httpx>=0.28.1",
    "pgvector>=0.4.2",
    "psycopg[binary]>=3.3.2",
    "pydantic>=2.12.5",
    "pydantic-settings>=2.12.0",
    "python-dotenv>=1.2.1",
    "python-multipart>=0.0.22",
    "redis>=7.0.1",
    "sqlalchemy>=2.0.45",
    "uvicorn>=0.41.0",
]

[dependency-groups]
dev = [
    "pytest>=9.0.2",
    "pytest-cov>=7.0.0",
    "ruff>=0.14.8",
]
```

Remove the existing Streamlit, Torch, notebook, and ML dependencies. Remove the PyTorch GPU uv index and sources.

- [ ] **Step 4: Add the minimal app**

Create `backend/__init__.py`:

```python
"""ParaWorks backend package."""
```

Create `backend/app/__init__.py`:

```python
"""ParaWorks backend application package."""
```

Create `backend/app/main.py`:

```python
from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(title='ParaWorks Harness')

    @app.get('/health')
    def health() -> dict[str, str]:
        return {'status': 'ok', 'service': 'paraworks'}

    return app


app = create_app()
```

- [ ] **Step 5: Update `README.md`**

```markdown
# ParaWorks

ParaWorks is a company-wide knowledge and history platform.

This repository starts with an Adapter-First Demo Harness: a local FastAPI backend, Next.js frontend, mock source connectors, review workflow, permission-filtered search, and verification runbooks.
```

- [ ] **Step 6: Verify and commit**

Run:

```powershell
uv lock
uv run pytest backend/tests/test_health.py -v
git add pyproject.toml uv.lock README.md backend/__init__.py backend/app/__init__.py backend/app/main.py backend/tests/test_health.py
git commit -m "chore: establish backend harness baseline"
```

Expected: PASS for `test_health_returns_ok`.

---

### Task 2: Local Runtime Harness

**Files:**
- Create: `.env.example`
- Create: `docker-compose.yml`
- Create: `docker/postgres/init/001_extensions.sql`
- Create: `docs/superpowers/runbooks/local-dev.md`
- Create: `docs/superpowers/runbooks/verification.md`

- [ ] **Step 1: Add environment example**

Create `.env.example`:

```dotenv
PARAWORKS_ENV=local
PARAWORKS_DEMO_MODE=true
PARAWORKS_API_HOST=127.0.0.1
PARAWORKS_API_PORT=8000
DATABASE_URL=postgresql+psycopg://paraworks:paraworks@localhost:5432/paraworks
REDIS_URL=redis://localhost:6379/0
MINIO_ENDPOINT=http://localhost:9000
MINIO_ACCESS_KEY=paraworks
MINIO_SECRET_KEY=paraworks-secret
MINIO_BUCKET=paraworks-sources
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
```

- [ ] **Step 2: Add Docker Compose**

Create `docker-compose.yml`:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg17
    container_name: paraworks-postgres
    environment:
      POSTGRES_DB: paraworks
      POSTGRES_USER: paraworks
      POSTGRES_PASSWORD: paraworks
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
      - ./docker/postgres/init:/docker-entrypoint-initdb.d:ro

  redis:
    image: redis:7-alpine
    container_name: paraworks-redis
    ports:
      - "6379:6379"

  minio:
    image: minio/minio:RELEASE.2026-04-12T18-03-45Z
    container_name: paraworks-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: paraworks
      MINIO_ROOT_PASSWORD: paraworks-secret
    ports:
      - "9000:9000"
      - "9001:9001"
    volumes:
      - minio-data:/data

volumes:
  postgres-data:
  minio-data:
```

Create `docker/postgres/init/001_extensions.sql`:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

- [ ] **Step 3: Add runbooks**

Create `docs/superpowers/runbooks/local-dev.md`:

```markdown
# Local Development Runbook

Run commands from `C:\potenup3\pj04-Paraworks`.

## Start Runtime Services

```powershell
docker compose up -d postgres redis minio
```

## Start Backend

```powershell
uv run uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

## Start Frontend

```powershell
cd frontend
npm run dev
```

## Demo Users

- `X-Demo-User: admin` can see `public`, `internal`, and `restricted` sources.
- `X-Demo-User: viewer` can see `public` and `internal` sources.
```

Create `docs/superpowers/runbooks/verification.md`:

```markdown
# ParaWorks Harness Verification

Run commands from `C:\potenup3\pj04-Paraworks`.

```powershell
docker compose config
uv run pytest backend/tests -v
cd frontend
npm run build
```
```

- [ ] **Step 4: Verify and commit**

Run:

```powershell
docker compose config
git add .env.example docker-compose.yml docker/postgres/init/001_extensions.sql docs/superpowers/runbooks/local-dev.md docs/superpowers/runbooks/verification.md
git commit -m "chore: add local runtime harness"
```

Expected: Compose config prints without errors.

---

### Task 3: Backend Domain Skeleton

**Files:**
- Create: `backend/app/core/config.py`
- Create: `backend/app/core/demo_auth.py`
- Create: `backend/app/db/base.py`
- Create: `backend/app/db/session.py`
- Create: `backend/app/models/enums.py`
- Create: `backend/app/models/source.py`
- Create: `backend/app/models/review.py`
- Create: `backend/app/models/jobs.py`
- Create: `backend/app/models/knowledge.py`
- Create: `backend/app/models/__init__.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_health.py`

- [ ] **Step 1: Extend the health test**

Modify `backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from backend.app.main import create_app


def test_health_returns_ok() -> None:
    client = TestClient(create_app())

    response = client.get('/health')

    assert response.status_code == 200
    assert response.json() == {
        'status': 'ok',
        'service': 'paraworks',
        'demo_mode': True,
    }
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
uv run pytest backend/tests/test_health.py -v
```

Expected: FAIL because `demo_mode` is absent.

- [ ] **Step 3: Add settings, demo auth, and SQLAlchemy base**

Create `backend/app/core/config.py`:

```python
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    paraworks_env: str = 'local'
    paraworks_demo_mode: bool = True
    database_url: str = 'postgresql+psycopg://paraworks:paraworks@localhost:5432/paraworks'
    redis_url: str = 'redis://localhost:6379/0'


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

Create `backend/app/core/demo_auth.py`:

```python
from dataclasses import dataclass

from fastapi import Header


@dataclass(frozen=True)
class DemoUser:
    id: str
    email: str
    role: str
    permission_levels: set[str]


USERS = {
    'admin': DemoUser('demo-admin', 'admin@paraworks.local', 'admin', {'public', 'internal', 'restricted'}),
    'viewer': DemoUser('demo-viewer', 'viewer@paraworks.local', 'viewer', {'public', 'internal'}),
}


def get_demo_user(x_demo_user: str = Header(default='admin')) -> DemoUser:
    return USERS.get(x_demo_user, USERS['viewer'])
```

Create `backend/app/db/base.py`:

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

Create `backend/app/db/session.py`:

```python
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

- [ ] **Step 4: Add models**

Create `backend/app/models/source.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class Source(Base):
    __tablename__ = 'sources'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    source_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    source_url: Mapped[str] = mapped_column(String(500))
    title: Mapped[str] = mapped_column(String(300))
    author: Mapped[str | None] = mapped_column(String(200), nullable=True)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    raw_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    documents: Mapped[list['Document']] = relationship(back_populates='source')


class Document(Base):
    __tablename__ = 'documents'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('sources.id'), index=True)
    title: Mapped[str] = mapped_column(String(300))
    current_version: Mapped[str] = mapped_column(String(64), default='v1')
    source: Mapped[Source] = relationship(back_populates='documents')
    versions: Mapped[list['DocumentVersion']] = relationship(back_populates='document')


class DocumentVersion(Base):
    __tablename__ = 'document_versions'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey('documents.id'), index=True)
    version: Mapped[str] = mapped_column(String(64), default='v1')
    body: Mapped[str] = mapped_column(Text)
    document: Mapped[Document] = relationship(back_populates='versions')
    chunks: Mapped[list['DocumentChunk']] = relationship(back_populates='version')


class DocumentChunk(Base):
    __tablename__ = 'document_chunks'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_id: Mapped[int] = mapped_column(ForeignKey('document_versions.id'), index=True)
    source_id: Mapped[int] = mapped_column(ForeignKey('sources.id'), index=True)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    source_snippet: Mapped[str] = mapped_column(Text)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    metadata_: Mapped[dict] = mapped_column('metadata', JSON, default=dict)
    version: Mapped[DocumentVersion] = relationship(back_populates='chunks')
```

Create `backend/app/models/review.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class ReviewItem(Base):
    __tablename__ = 'review_items'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    item_type: Mapped[str] = mapped_column(String(64), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    source_links: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_snippets: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float] = mapped_column(Float)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default='pending_review', index=True)
    reviewer_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

Create `backend/app/models/jobs.py`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class SyncJob(Base):
    __tablename__ = 'sync_jobs'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    connector_type: Mapped[str] = mapped_column(String(32), index=True)
    status: Mapped[str] = mapped_column(String(32), default='queued')
    message: Mapped[str] = mapped_column(String(300), default='queued')
    progress_pct: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

Create `backend/app/models/knowledge.py` with the same base fields for `DecisionRecord`, `HistoryEvent`, `TimelineEvent`, and `Todo`:

```python
from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.app.db.base import Base


class DecisionRecord(Base):
    __tablename__ = 'decision_records'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    decision_summary: Mapped[str] = mapped_column(Text)
    source_links: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_snippets: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float] = mapped_column(Float)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    review_status: Mapped[str] = mapped_column(String(32), default='pending_review')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class HistoryEvent(Base):
    __tablename__ = 'history_events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    reason: Mapped[str] = mapped_column(Text)
    source_links: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_snippets: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float] = mapped_column(Float)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    review_status: Mapped[str] = mapped_column(String(32), default='pending_review')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class TimelineEvent(Base):
    __tablename__ = 'timeline_events'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    result_summary: Mapped[str] = mapped_column(Text)
    source_links: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_snippets: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float] = mapped_column(Float)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    review_status: Mapped[str] = mapped_column(String(32), default='pending_review')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Todo(Base):
    __tablename__ = 'todos'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    priority: Mapped[str] = mapped_column(String(32))
    priority_reason: Mapped[str] = mapped_column(Text)
    source_links: Mapped[list[str]] = mapped_column(JSON, default=list)
    source_snippets: Mapped[list[str]] = mapped_column(JSON, default=list)
    confidence_score: Mapped[float] = mapped_column(Float)
    permission_level: Mapped[str] = mapped_column(String(32), index=True)
    review_status: Mapped[str] = mapped_column(String(32), default='pending_review')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 5: Wire health to settings and commit**

Modify `backend/app/main.py`:

```python
from fastapi import FastAPI

from backend.app.core.config import get_settings


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title='ParaWorks Harness')

    @app.get('/health')
    def health() -> dict[str, bool | str]:
        return {'status': 'ok', 'service': 'paraworks', 'demo_mode': settings.paraworks_demo_mode}

    return app


app = create_app()
```

Run:

```powershell
uv run pytest backend/tests/test_health.py -v
git add backend/app backend/tests/test_health.py
git commit -m "feat: add backend domain skeleton"
```

Expected: PASS.

---

### Task 4: Mock Connectors and Seed Scenarios

**Files:**
- Create: `backend/app/connectors/base.py`
- Create: `backend/app/connectors/mock.py`
- Create: `backend/app/connectors/__init__.py`
- Create: `backend/app/seeds/mock_sources.py`
- Create: `docs/superpowers/runbooks/demo-seed.md`
- Test: `backend/tests/test_mock_connectors.py`

- [ ] **Step 1: Write connector tests**

Create `backend/tests/test_mock_connectors.py`:

```python
from backend.app.connectors.mock import get_mock_connector


def test_mock_drive_connector_returns_permission_leakage_case() -> None:
    connector = get_mock_connector('drive')
    events = connector.fetch_events()

    restricted = next(event for event in events if event.source_id == 'drive-permission-leakage-case')
    assert restricted.permission_level == 'restricted'
    assert restricted.source_url.startswith('https://drive.mock/')


def test_all_mock_connectors_return_source_evidence() -> None:
    for connector_type in ['drive', 'gmail', 'slack', 'calendar']:
        events = get_mock_connector(connector_type).fetch_events()

        assert events
        assert all(event.source_url for event in events)
        assert all(event.body for event in events)
```

- [ ] **Step 2: Run the tests to verify they fail**

```powershell
uv run pytest backend/tests/test_mock_connectors.py -v
```

Expected: FAIL because `backend.app.connectors` does not exist.

- [ ] **Step 3: Add connector contract and seeds**

Create `backend/app/connectors/base.py`:

```python
from collections.abc import Protocol
from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class SourceEvent:
    source_type: str
    source_id: str
    source_url: str
    title: str
    body: str
    author: str | None
    participants: list[str]
    timestamp: datetime
    permission_level: str
    raw_metadata: dict = field(default_factory=dict)


class Connector(Protocol):
    source_type: str

    def fetch_events(self) -> list[SourceEvent]:
        raise NotImplementedError
```

Create `backend/app/seeds/mock_sources.py`:

```python
from datetime import datetime, timezone

from backend.app.connectors.base import SourceEvent


SEED_EVENTS = [
    SourceEvent('slack', 'slack-project-alpha-redis-thread', 'https://slack.mock/archives/alpha/p1', 'Project Alpha Redis decision thread', 'Redis was selected because job status updates need low latency and Celery already depends on Redis.', 'pm@paraworks.local', ['pm@paraworks.local', 'backend@paraworks.local'], datetime(2026, 4, 20, 9, 0, tzinfo=timezone.utc), 'internal', {'scenario': 'project-alpha-redis-decision'}),
    SourceEvent('gmail', 'gmail-project-alpha-redis-summary', 'https://gmail.mock/thread/alpha-redis', 'Redis decision summary', 'Redis supports queues and SSE job status fanout. PostgreSQL remains the system of record.', 'lead@paraworks.local', ['lead@paraworks.local'], datetime(2026, 4, 20, 10, 30, tzinfo=timezone.utc), 'internal', {'scenario': 'project-alpha-redis-decision'}),
    SourceEvent('drive', 'drive-project-alpha-architecture-note', 'https://drive.mock/doc/project-alpha-architecture-note', 'Project Alpha architecture note', 'The team rejected direct database polling for progress updates.', 'architect@paraworks.local', ['architect@paraworks.local'], datetime(2026, 4, 21, 2, 0, tzinfo=timezone.utc), 'internal', {'scenario': 'project-alpha-redis-decision'}),
    SourceEvent('calendar', 'calendar-project-beta-scope-meeting', 'https://calendar.mock/event/project-beta-scope-meeting', 'Project Beta scope review', 'Advanced document diff UI moves out of MVP. Review Queue and Source Evidence Drawer remain required.', 'pm@paraworks.local', ['pm@paraworks.local'], datetime(2026, 4, 22, 6, 0, tzinfo=timezone.utc), 'internal', {'scenario': 'project-beta-scope-cut'}),
    SourceEvent('slack', 'slack-project-beta-followup', 'https://slack.mock/archives/beta/p1', 'Project Beta follow-up', 'Follow-up todo: verify evidence inspection before launch.', 'producer@paraworks.local', ['producer@paraworks.local'], datetime(2026, 4, 22, 7, 0, tzinfo=timezone.utc), 'internal', {'scenario': 'project-beta-scope-cut'}),
    SourceEvent('drive', 'drive-permission-leakage-case', 'https://drive.mock/doc/restricted-customer-escalation', 'Restricted customer escalation memo', 'Restricted memo: confidential pricing must not appear for viewer users.', 'exec@paraworks.local', ['exec@paraworks.local'], datetime(2026, 4, 23, 1, 0, tzinfo=timezone.utc), 'restricted', {'scenario': 'permission-leakage-case'}),
]
```

Create `backend/app/connectors/mock.py`:

```python
from dataclasses import dataclass

from backend.app.connectors.base import SourceEvent
from backend.app.seeds.mock_sources import SEED_EVENTS


CONNECTOR_TYPES = {'drive', 'gmail', 'slack', 'calendar'}


@dataclass(frozen=True)
class MockConnector:
    source_type: str

    def fetch_events(self) -> list[SourceEvent]:
        return [event for event in SEED_EVENTS if event.source_type == self.source_type]


def get_mock_connector(source_type: str) -> MockConnector:
    if source_type not in CONNECTOR_TYPES:
        raise ValueError(f'Unsupported mock connector: {source_type}')
    return MockConnector(source_type)
```

Create `backend/app/connectors/__init__.py`:

```python
from backend.app.connectors.base import Connector, SourceEvent
from backend.app.connectors.mock import get_mock_connector

__all__ = ['Connector', 'SourceEvent', 'get_mock_connector']
```

- [ ] **Step 4: Add seed runbook and commit**

Create `docs/superpowers/runbooks/demo-seed.md`:

```markdown
# Demo Seed Runbook

The first harness uses deterministic mock source events.

Scenarios:

- `project-alpha-redis-decision`
- `project-beta-scope-cut`
- `permission-leakage-case`

Demo users:

- `X-Demo-User: admin`
- `X-Demo-User: viewer`
```

Run:

```powershell
uv run pytest backend/tests/test_mock_connectors.py -v
git add backend/app/connectors backend/app/seeds backend/tests/test_mock_connectors.py docs/superpowers/runbooks/demo-seed.md
git commit -m "feat: add mock source connectors"
```

Expected: PASS.

---

### Task 5: Ingestion, Review API, Search, and SSE

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_mock_sync.py`
- Create: `backend/tests/test_review.py`
- Create: `backend/tests/test_search_permissions.py`
- Create: `backend/tests/test_stream.py`
- Create: `backend/app/ingestion/service.py`
- Create: `backend/app/knowledge/extractor.py`
- Create: `backend/app/permissions/service.py`
- Create: `backend/app/schemas/search.py`
- Create: `backend/app/api/v1/router.py`
- Create: `backend/app/api/v1/integrations.py`
- Create: `backend/app/api/v1/review.py`
- Create: `backend/app/api/v1/search.py`
- Create: `backend/app/api/v1/dashboard.py`
- Create: `backend/app/api/v1/stream.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Add test fixtures**

Create `backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.db.base import Base
from backend.app.db.session import get_db
from backend.app.main import create_app


@pytest.fixture
def db_session() -> Session:
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client(db_session: Session) -> TestClient:
    app = create_app()

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)
```

- [ ] **Step 2: Add failing API tests**

Create `backend/tests/test_mock_sync.py`, `backend/tests/test_review.py`, `backend/tests/test_search_permissions.py`, and `backend/tests/test_stream.py`:

```python
def test_mock_slack_sync_creates_pending_review_items(client) -> None:
    response = client.post('/api/v1/integrations/slack/sync')
    assert response.status_code == 200
    assert response.json()['status'] == 'complete'

    review_response = client.get('/api/v1/review?status=pending_review')
    assert review_response.status_code == 200
    assert review_response.json()['items']
```

```python
def test_approve_review_item_changes_status(client) -> None:
    client.post('/api/v1/integrations/slack/sync')
    item = client.get('/api/v1/review?status=pending_review').json()['items'][0]

    response = client.post(f"/api/v1/review/{item['id']}/approve")

    assert response.status_code == 200
    assert response.json()['status'] == 'approved'


def test_reject_review_item_changes_status(client) -> None:
    client.post('/api/v1/integrations/slack/sync')
    item = client.get('/api/v1/review?status=pending_review').json()['items'][0]

    response = client.post(f"/api/v1/review/{item['id']}/reject")

    assert response.status_code == 200
    assert response.json()['status'] == 'rejected'
```

```python
def test_viewer_search_cannot_see_restricted_drive_content(client) -> None:
    client.post('/api/v1/integrations/drive/sync')

    response = client.post('/api/v1/search', headers={'X-Demo-User': 'viewer'}, json={'query': 'confidential pricing'})

    assert response.status_code == 200
    assert response.json()['results'] == []
    assert response.json()['permission_notice'] == 'Some sources may be hidden by permissions.'


def test_admin_search_can_see_restricted_drive_content(client) -> None:
    client.post('/api/v1/integrations/drive/sync')

    response = client.post('/api/v1/search', headers={'X-Demo-User': 'admin'}, json={'query': 'confidential pricing'})

    assert response.status_code == 200
    assert len(response.json()['results']) == 1
```

```python
def test_job_status_stream_returns_sse_event(client) -> None:
    sync = client.post('/api/v1/integrations/slack/sync').json()

    response = client.get(f"/api/v1/stream/job-status?job_id={sync['job_id']}")

    assert response.status_code == 200
    assert 'text/event-stream' in response.headers['content-type']
    assert 'event: progress' in response.text
```

Run:

```powershell
uv run pytest backend/tests -v
```

Expected: FAIL because API routes are absent.

- [ ] **Step 3: Add services**

Create `backend/app/knowledge/extractor.py`:

```python
from backend.app.models.source import DocumentChunk


def build_review_payloads(chunks: list[DocumentChunk]) -> list[dict]:
    text = ' '.join(chunk.text for chunk in chunks)
    source_links = [chunk.metadata_['source_url'] for chunk in chunks]
    source_snippets = [chunk.source_snippet for chunk in chunks]
    permission_level = 'restricted' if any(chunk.permission_level == 'restricted' for chunk in chunks) else 'internal'
    payloads: list[dict] = []

    if 'Redis' in text:
        payloads.append({'item_type': 'decision_record', 'payload': {'title': 'Use Redis for queues and job progress', 'decision_summary': 'Redis supports Celery coordination and job status updates.'}, 'source_links': source_links, 'source_snippets': source_snippets, 'confidence_score': 0.86, 'permission_level': permission_level})
    if 'scope' in text.lower():
        payloads.append({'item_type': 'history_event', 'payload': {'title': 'Project Beta advanced diff UI moved out of MVP', 'reason': 'The team kept Review Queue and Source Evidence Drawer in scope.'}, 'source_links': source_links, 'source_snippets': source_snippets, 'confidence_score': 0.82, 'permission_level': permission_level})
    if 'todo' in text.lower() or 'follow-up' in text.lower():
        payloads.append({'item_type': 'todo', 'payload': {'title': 'Verify evidence inspection before launch', 'priority': 'high', 'priority_reason': 'Review confidence depends on source evidence.'}, 'source_links': source_links, 'source_snippets': source_snippets, 'confidence_score': 0.8, 'permission_level': permission_level})
    return payloads
```

Create `backend/app/ingestion/service.py`:

```python
from sqlalchemy.orm import Session

from backend.app.connectors.base import SourceEvent
from backend.app.knowledge.extractor import build_review_payloads
from backend.app.models.review import ReviewItem
from backend.app.models.source import Document, DocumentChunk, DocumentVersion, Source


def ingest_events(db: Session, events: list[SourceEvent]) -> int:
    chunks: list[DocumentChunk] = []
    for event in events:
        source = Source(source_type=event.source_type, source_id=event.source_id, source_url=event.source_url, title=event.title, author=event.author, permission_level=event.permission_level, raw_metadata={**event.raw_metadata, 'participants': event.participants})
        db.add(source)
        db.flush()
        document = Document(source_id=source.id, title=event.title, current_version='v1')
        db.add(document)
        db.flush()
        version = DocumentVersion(document_id=document.id, version='v1', body=event.body)
        db.add(version)
        db.flush()
        chunk = DocumentChunk(version_id=version.id, source_id=source.id, chunk_index=0, text=event.body, source_snippet=event.body[:240], permission_level=event.permission_level, metadata_={'source_url': event.source_url, 'source_type': event.source_type, 'scenario': event.raw_metadata.get('scenario')})
        db.add(chunk)
        chunks.append(chunk)
    db.flush()
    review_payloads = build_review_payloads(chunks)
    for payload in review_payloads:
        db.add(ReviewItem(status='pending_review', **payload))
    db.commit()
    return len(review_payloads)
```

Create `backend/app/permissions/service.py`:

```python
from backend.app.core.demo_auth import DemoUser


def can_access_permission(user: DemoUser, permission_level: str) -> bool:
    return permission_level in user.permission_levels
```

- [ ] **Step 4: Add API routes**

Create `backend/app/api/v1/integrations.py`:

```python
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.connectors.mock import CONNECTOR_TYPES, get_mock_connector
from backend.app.db.session import get_db
from backend.app.ingestion.service import ingest_events
from backend.app.models.jobs import SyncJob

router = APIRouter(prefix='/integrations', tags=['integrations'])


@router.get('')
def list_integrations() -> dict[str, list[dict[str, str]]]:
    return {'integrations': [{'type': item, 'mode': 'mock', 'status': 'ready'} for item in sorted(CONNECTOR_TYPES)]}


@router.post('/{connector_type}/sync')
def sync_connector(connector_type: str, db: Session = Depends(get_db)) -> dict[str, int | str]:
    connector = get_mock_connector(connector_type)
    job = SyncJob(job_id=str(uuid4()), connector_type=connector_type, status='running', message='fetching mock source events', progress_pct=25)
    db.add(job)
    db.commit()

    created_review_items = ingest_events(db, connector.fetch_events())
    job.status = 'complete'
    job.message = 'complete'
    job.progress_pct = 100
    db.commit()

    return {'job_id': job.job_id, 'connector_type': connector_type, 'status': job.status, 'created_review_items': created_review_items}
```

Create `backend/app/api/v1/review.py`:

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.models.review import ReviewItem

router = APIRouter(prefix='/review', tags=['review'])


def serialize_review_item(item: ReviewItem) -> dict:
    return {'id': item.id, 'item_type': item.item_type, 'payload': item.payload, 'source_links': item.source_links, 'source_snippets': item.source_snippets, 'confidence_score': item.confidence_score, 'permission_level': item.permission_level, 'status': item.status}


@router.get('')
def list_review_items(status: str = 'pending_review', db: Session = Depends(get_db)) -> dict[str, list[dict]]:
    items = db.scalars(select(ReviewItem).where(ReviewItem.status == status)).all()
    return {'items': [serialize_review_item(item) for item in items]}


@router.post('/{item_id}/approve')
def approve_review_item(item_id: int, db: Session = Depends(get_db), user: DemoUser = Depends(get_demo_user)) -> dict:
    item = db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='review item not found')
    if not item.source_links or not item.source_snippets:
        raise HTTPException(status_code=400, detail='source evidence is required')
    item.status = 'approved'
    item.reviewer_id = user.id
    item.reviewed_at = datetime.utcnow()
    db.commit()
    return serialize_review_item(item)


@router.post('/{item_id}/reject')
def reject_review_item(item_id: int, db: Session = Depends(get_db), user: DemoUser = Depends(get_demo_user)) -> dict:
    item = db.get(ReviewItem, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail='review item not found')
    item.status = 'rejected'
    item.reviewer_id = user.id
    item.reviewed_at = datetime.utcnow()
    db.commit()
    return serialize_review_item(item)
```

Create `backend/app/schemas/search.py`:

```python
from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
```

Create `backend/app/api/v1/search.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.core.demo_auth import DemoUser, get_demo_user
from backend.app.db.session import get_db
from backend.app.models.source import DocumentChunk
from backend.app.permissions.service import can_access_permission
from backend.app.schemas.search import SearchRequest

router = APIRouter(prefix='/search', tags=['search'])


@router.post('')
def search(request: SearchRequest, db: Session = Depends(get_db), user: DemoUser = Depends(get_demo_user)) -> dict:
    query = request.query.lower()
    chunks = db.scalars(select(DocumentChunk)).all()
    results = []
    hidden_count = 0
    for chunk in chunks:
        if query not in chunk.text.lower():
            continue
        if not can_access_permission(user, chunk.permission_level):
            hidden_count += 1
            continue
        results.append({'chunk_id': chunk.id, 'title': chunk.metadata_.get('scenario', 'source result'), 'source_url': chunk.metadata_['source_url'], 'source_snippet': chunk.source_snippet, 'permission_level': chunk.permission_level})
    return {'query': request.query, 'results': results, 'permission_notice': 'Some sources may be hidden by permissions.' if hidden_count else None}
```

Create `backend/app/api/v1/dashboard.py`:

```python
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.jobs import SyncJob
from backend.app.models.review import ReviewItem
from backend.app.models.source import Source

router = APIRouter(prefix='/dashboard', tags=['dashboard'])


@router.get('')
def dashboard(db: Session = Depends(get_db)) -> dict:
    source_counts = dict(db.execute(select(Source.source_type, func.count(Source.id)).group_by(Source.source_type)).all())
    pending_review_count = db.scalar(select(func.count(ReviewItem.id)).where(ReviewItem.status == 'pending_review')) or 0
    recent_jobs = db.scalars(select(SyncJob).order_by(SyncJob.created_at.desc()).limit(5)).all()
    return {'source_counts': source_counts, 'pending_review_count': pending_review_count, 'recent_jobs': [{'job_id': job.job_id, 'connector_type': job.connector_type, 'status': job.status, 'progress_pct': job.progress_pct} for job in recent_jobs]}
```

Create `backend/app/api/v1/stream.py`:

```python
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.models.jobs import SyncJob

router = APIRouter(prefix='/stream', tags=['stream'])


@router.get('/job-status')
def job_status(job_id: str, db: Session = Depends(get_db)) -> StreamingResponse:
    job = db.scalar(select(SyncJob).where(SyncJob.job_id == job_id))
    if job is None:
        raise HTTPException(status_code=404, detail='sync job not found')

    def events():
        progress = {'type': 'progress', 'pct': job.progress_pct, 'message': job.message}
        yield f"event: progress\ndata: {json.dumps(progress, separators=(',', ':'))}\n\n"
        yield 'event: done\ndata: {"type":"done"}\n\n'

    return StreamingResponse(events(), media_type='text/event-stream')
```

Create `backend/app/api/v1/router.py`:

```python
from fastapi import APIRouter

from backend.app.api.v1 import dashboard, integrations, review, search, stream

api_router = APIRouter(prefix='/api/v1')
api_router.include_router(dashboard.router)
api_router.include_router(integrations.router)
api_router.include_router(review.router)
api_router.include_router(search.router)
api_router.include_router(stream.router)
```

Modify `backend/app/main.py` to include `api_router`.

- [ ] **Step 5: Verify and commit**

Run:

```powershell
uv run pytest backend/tests -v
git add backend/app backend/tests
git commit -m "feat: add mock ingestion and review APIs"
```

Expected: all backend tests PASS.

---

### Task 6: Frontend MVP Harness

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/tsconfig.json`
- Create: `frontend/next.config.ts`
- Create: `frontend/postcss.config.mjs`
- Create: `frontend/tailwind.config.ts`
- Create: `frontend/src/app/layout.tsx`
- Create: `frontend/src/app/globals.css`
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/app/dashboard/page.tsx`
- Create: `frontend/src/app/integrations/page.tsx`
- Create: `frontend/src/app/review/page.tsx`
- Create: `frontend/src/app/search/page.tsx`
- Create: `frontend/src/components/layout/AppShell.tsx`
- Create: `frontend/src/components/shared/SourceEvidenceDrawer.tsx`
- Create: `frontend/src/lib/api/client.ts`
- Create: `frontend/src/lib/api/types.ts`
- Create: `frontend/src/hooks/useJobStatus.ts`

- [ ] **Step 1: Add package and config**

Create `frontend/package.json`:

```json
{
  "name": "paraworks-frontend",
  "version": "0.1.0",
  "private": true,
  "scripts": {"dev": "next dev", "build": "next build", "lint": "next lint"},
  "dependencies": {
    "@tanstack/react-query": "^6.0.0",
    "date-fns": "^4.1.0",
    "lucide-react": "^0.581.0",
    "next": "^15.5.9",
    "react": "^19.2.1",
    "react-dom": "^19.2.1",
    "zod": "^4.3.0",
    "zustand": "^5.0.9"
  },
  "devDependencies": {
    "@types/node": "^24.10.1",
    "@types/react": "^19.2.7",
    "@types/react-dom": "^19.2.3",
    "autoprefixer": "^10.4.22",
    "postcss": "^8.5.6",
    "tailwindcss": "^3.4.18",
    "typescript": "^5.9.3"
  }
}
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "es2022"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "paths": {"@/*": ["./src/*"]}
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}
```

Create `frontend/next.config.ts`:

```typescript
import type {NextConfig} from 'next';

const nextConfig: NextConfig = {};

export default nextConfig;
```

Create `frontend/postcss.config.mjs`:

```javascript
const config = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};

export default config;
```

Create `frontend/tailwind.config.ts`:

```typescript
import type {Config} from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx}'],
  theme: {extend: {}},
  plugins: [],
};

export default config;
```

- [ ] **Step 2: Add API client and shell**

Create `frontend/src/lib/api/client.ts`:

```typescript
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://127.0.0.1:8000';

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {headers: {'X-Demo-User': 'admin'}, cache: 'no-store'});
  if (!response.ok) throw new Error(`GET ${path} failed`);
  return response.json() as Promise<T>;
}

export async function apiPost<T>(path: string, body?: unknown, demoUser = 'admin'): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json', 'X-Demo-User': demoUser},
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`POST ${path} failed`);
  return response.json() as Promise<T>;
}
```

Create `frontend/src/components/layout/AppShell.tsx`:

```tsx
import Link from 'next/link';
import {Database, LayoutDashboard, Search, ShieldCheck} from 'lucide-react';

const nav = [
  {href: '/dashboard', label: 'Dashboard', icon: LayoutDashboard},
  {href: '/integrations', label: 'Integrations', icon: Database},
  {href: '/review', label: 'Review', icon: ShieldCheck},
  {href: '/search', label: 'Search', icon: Search},
];

export function AppShell({children}: {children: React.ReactNode}) {
  return (
    <div className="min-h-screen grid grid-cols-[240px_1fr]">
      <aside className="border-r border-neutral-200 bg-white px-4 py-5">
        <div className="text-lg font-semibold">ParaWorks</div>
        <nav className="mt-6 space-y-1">
          {nav.map((item) => {
            const Icon = item.icon;
            return <Link key={item.href} href={item.href} className="flex items-center gap-2 rounded-md px-3 py-2 text-sm hover:bg-neutral-100"><Icon size={16} />{item.label}</Link>;
          })}
        </nav>
      </aside>
      <main className="p-6">{children}</main>
    </div>
  );
}
```

- [ ] **Step 3: Add pages**

Create `frontend/src/app/dashboard/page.tsx`:

```tsx
import {apiGet} from '@/lib/api/client';

export default async function DashboardPage() {
  const data = await apiGet<{source_counts: Record<string, number>; pending_review_count: number; recent_jobs: unknown[]}>('/api/v1/dashboard');
  const sourceCount = Object.values(data.source_counts).reduce((sum, count) => sum + count, 0);
  return <section className="space-y-6"><h1 className="text-2xl font-semibold">Dashboard</h1><div className="grid grid-cols-3 gap-4"><div className="rounded-md border bg-white p-4">Sources: {sourceCount}</div><div className="rounded-md border bg-white p-4">Pending review: {data.pending_review_count}</div><div className="rounded-md border bg-white p-4">Recent jobs: {data.recent_jobs.length}</div></div></section>;
}
```

Create `frontend/src/app/integrations/page.tsx`:

```tsx
'use client';

import {useState} from 'react';
import {RefreshCw} from 'lucide-react';
import {apiPost} from '@/lib/api/client';
import {useJobStatus} from '@/hooks/useJobStatus';

const connectors = ['drive', 'gmail', 'slack', 'calendar'];

export default function IntegrationsPage() {
  const [jobId, setJobId] = useState<string | null>(null);
  const status = useJobStatus(jobId);
  async function sync(type: string) {
    const result = await apiPost<{job_id: string}>(`/api/v1/integrations/${type}/sync`);
    setJobId(result.job_id);
  }
  return <section className="space-y-6"><h1 className="text-2xl font-semibold">Integrations</h1><div className="grid grid-cols-4 gap-4">{connectors.map((type) => <button key={type} onClick={() => sync(type)} className="rounded-md border bg-white p-4 text-left"><RefreshCw size={18} /><div className="mt-3 font-medium capitalize">{type}</div><div className="text-sm text-neutral-500">Mock sync</div></button>)}</div>{status ? <pre className="rounded-md bg-neutral-900 p-4 text-sm text-white">{status}</pre> : null}</section>;
}
```

Create `frontend/src/app/review/page.tsx`:

```tsx
import {SourceEvidenceDrawer} from '@/components/shared/SourceEvidenceDrawer';
import {apiGet} from '@/lib/api/client';

type ReviewItem = {id: number; item_type: string; payload: Record<string, string>; source_links: string[]; source_snippets: string[]; confidence_score: number};

export default async function ReviewPage() {
  const data = await apiGet<{items: ReviewItem[]}>('/api/v1/review?status=pending_review');
  return <section className="space-y-6"><h1 className="text-2xl font-semibold">Review Queue</h1>{data.items.map((item) => <article key={item.id} className="rounded-md border bg-white p-4"><div className="text-sm text-neutral-500">{item.item_type}</div><h2 className="text-lg font-semibold">{item.payload.title}</h2><div className="text-sm">{Math.round(item.confidence_score * 100)}% confidence</div><SourceEvidenceDrawer snippets={item.source_snippets} links={item.source_links} /></article>)}</section>;
}
```

Create `frontend/src/app/search/page.tsx`:

```tsx
'use client';

import {useState} from 'react';
import {apiPost} from '@/lib/api/client';

type SearchResult = {chunk_id: number; title: string; source_url: string; source_snippet: string; permission_level: string};

export default function SearchPage() {
  const [query, setQuery] = useState('Redis');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [notice, setNotice] = useState<string | null>(null);
  async function runSearch() {
    const data = await apiPost<{results: SearchResult[]; permission_notice: string | null}>('/api/v1/search', {query}, 'viewer');
    setResults(data.results);
    setNotice(data.permission_notice);
  }
  return <section className="space-y-6"><h1 className="text-2xl font-semibold">Search</h1><div className="flex gap-2"><input value={query} onChange={(event) => setQuery(event.target.value)} className="w-full rounded-md border px-3 py-2" /><button onClick={runSearch} className="rounded-md bg-neutral-900 px-4 py-2 text-white">Search</button></div>{notice ? <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-sm">{notice}</div> : null}{results.map((result) => <article key={result.chunk_id} className="rounded-md border bg-white p-4"><h2 className="font-semibold">{result.title}</h2><p className="mt-2 text-sm">{result.source_snippet}</p><a href={result.source_url} className="text-blue-700 underline">Source</a></article>)}</section>;
}
```

Use `SourceEvidenceDrawer` for snippets and links:

```tsx
export function SourceEvidenceDrawer({snippets, links}: {snippets: string[]; links: string[]}) {
  return (
    <div className="mt-3 rounded-md border border-neutral-200 bg-neutral-50 p-3">
      <div className="text-sm font-medium">Source evidence</div>
      {snippets.map((snippet, index) => (
        <div key={`${links[index]}-${index}`} className="mt-2 text-sm text-neutral-700">
          <a href={links[index]} className="text-blue-700 underline">Source {index + 1}</a>
          <p className="mt-1">{snippet}</p>
        </div>
      ))}
    </div>
  );
}
```

- [ ] **Step 4: Verify and commit**

Run:

```powershell
cd frontend
npm install
npm run build
git add frontend
git commit -m "feat: add frontend demo harness"
```

Expected: Next.js build completes.

---

### Task 7: ADR and Final Verification

**Files:**
- Create: `docs/superpowers/decisions/ADR-0001-adapter-first-demo-harness.md`
- Modify: `docs/superpowers/runbooks/verification.md`

- [ ] **Step 1: Create ADR**

Create `docs/superpowers/decisions/ADR-0001-adapter-first-demo-harness.md`:

```markdown
# ADR-0001: Adapter-First Demo Harness

## Status

Accepted

## Context

ParaWorks needs to validate company-wide knowledge workflows before production integrations are ready. The core risk is whether source-backed review, permission-filtered search, and evidence inspection work as one coherent service.

## Decision

The first harness uses mock connectors that implement the same source-event contract future real connectors will implement. The backend normalizes source events, creates deterministic review candidates, enforces permission filtering, and exposes demo UI APIs.

## Consequences

- Real connectors can be added without rewriting ingestion and review logic.
- Tests can run without external SaaS credentials.
- Permission leakage checks are part of the baseline harness.
- LangGraph integration can be added after deterministic behavior is covered.
```

- [ ] **Step 2: Run full verification**

Run:

```powershell
docker compose config
uv run pytest backend/tests -v
cd frontend
npm run build
git status --short
```

Expected:

- Compose config succeeds.
- Backend tests pass.
- Frontend build succeeds.
- Git status shows only intended files before commit.

- [ ] **Step 3: Commit**

```powershell
git add docs/superpowers/decisions/ADR-0001-adapter-first-demo-harness.md docs/superpowers/runbooks/verification.md
git commit -m "docs: add harness decision and verification runbook"
```

---

## Plan Self-Review

### Spec Coverage

- Local runtime harness: Tasks 1 and 2.
- Mock-data demo harness: Tasks 4 and 5.
- Review Queue: Task 5.
- Search and permission guard: Task 5.
- SSE job status: Task 5.
- Frontend dashboard, integrations, review, and search: Task 6.
- Codex work harness docs and ADR: Task 7.

### Type Consistency

- Connector source types are `drive`, `gmail`, `slack`, and `calendar`.
- Review statuses are `pending_review`, `approved`, `rejected`, and `needs_more_evidence`.
- Permission levels are `public`, `internal`, and `restricted`.
- Demo users are `admin` and `viewer`.

### Verification Summary

The implementation is complete when these commands pass:

```powershell
docker compose config
uv run pytest backend/tests -v
cd frontend
npm run build
```

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-30-paraworks-harness.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
