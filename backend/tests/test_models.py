from collections.abc import Generator
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.db.base import Base
from backend.app.models import ReviewItem, Source, SyncJob


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    engine = create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    with SessionLocal() as session:
        yield session

    Base.metadata.drop_all(engine)


def test_source_raw_metadata_tracks_in_place_mutation(db_session: Session) -> None:
    source = Source(
        source_type='drive',
        source_id='drive-1',
        source_url='https://example.test/drive-1',
        title='Source',
        permission_level='internal',
        raw_metadata={'labels': ['alpha']},
    )
    db_session.add(source)
    db_session.commit()

    source.raw_metadata['synced'] = True
    db_session.commit()
    db_session.refresh(source)

    assert source.raw_metadata['synced'] is True


def test_review_item_source_snippets_tracks_in_place_mutation(db_session: Session) -> None:
    review_item = ReviewItem(
        item_type='todo',
        payload={'title': 'Follow up'},
        source_links=[],
        source_snippets=['initial snippet'],
        confidence_score=0.91,
        permission_level='internal',
    )
    db_session.add(review_item)
    db_session.commit()

    review_item.source_snippets.append('new snippet')
    db_session.commit()
    db_session.refresh(review_item)

    assert review_item.source_snippets == ['initial snippet', 'new snippet']


def test_sync_job_updated_at_refreshes_on_update(db_session: Session) -> None:
    old_updated_at = datetime(2020, 1, 1)
    sync_job = SyncJob(
        job_id='sync-1',
        connector_type='drive',
        updated_at=old_updated_at,
    )
    db_session.add(sync_job)
    db_session.commit()

    sync_job.status = 'running'
    sync_job.progress_pct = 25
    db_session.commit()
    db_session.refresh(sync_job)

    assert sync_job.updated_at > old_updated_at
