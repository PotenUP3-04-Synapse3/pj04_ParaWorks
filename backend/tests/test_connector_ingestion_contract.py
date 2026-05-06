from dataclasses import dataclass
from datetime import UTC, datetime

import pytest
from sqlalchemy.orm import Session

from backend.app.connectors.base import ConnectorManifest, SourceEvent
from backend.app.connectors.registry import (
    get_connector_manifest,
    list_connector_manifests,
)
from backend.app.ingestion.sync import sync_connector_events
from backend.app.models import DocumentChunk, Source, SyncJob


def source_event(source_id: str = 'contract-event-1') -> SourceEvent:
    return SourceEvent(
        source_type='slack',
        source_id=source_id,
        source_url=f'https://slack.mock/{source_id}',
        title='Contract event',
        body='Redis incident timeline should enter company memory.',
        author='u123',
        participants=['u123'],
        timestamp=datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
        permission_level='internal',
        raw_metadata={
            'channel_id': 'C123',
            'external_updated_at': '2026-05-01T09:00:00+00:00',
            'ts': '1777600800.000100',
        },
    )


@dataclass(frozen=True)
class ContractConnector:
    source_type: str = 'slack'
    manifest: ConnectorManifest = ConnectorManifest(
        connector_type='slack',
        display_name='Slack',
        mode='mock',
        auth_type='oauth',
        required_scopes=('channels:history', 'groups:history', 'im:history', 'mpim:history'),
        sync_strategy='incremental',
        cost_policy='Fetch source deltas first; embed only changed chunks after review approval.',
    )

    def fetch_events(self) -> list[SourceEvent]:
        return [source_event()]


@dataclass
class IncrementalContractConnector:
    observed_cursor: dict[str, str] | None = None
    source_type: str = 'slack'
    manifest: ConnectorManifest = ConnectorManifest(
        connector_type='slack',
        display_name='Slack',
        mode='live',
        auth_type='oauth',
        required_scopes=('channels:history', 'groups:history', 'im:history', 'mpim:history'),
        sync_strategy='incremental',
        cost_policy='Fetch source deltas first; embed only changed chunks after review approval.',
    )

    def fetch_events(self) -> list[SourceEvent]:
        raise AssertionError('incremental connector should receive a sync cursor')

    def fetch_events_since(self, latest_timestamps_by_partition: dict[str, str]) -> list[SourceEvent]:
        self.observed_cursor = latest_timestamps_by_partition
        return [source_event('contract-event-2')]


@dataclass(frozen=True)
class FailingConnector:
    source_type: str = 'gmail'
    manifest: ConnectorManifest = ConnectorManifest(
        connector_type='gmail',
        display_name='Gmail',
        mode='live',
        auth_type='oauth',
        required_scopes=('gmail.readonly',),
        sync_strategy='incremental',
        cost_policy='Fetch message deltas before review extraction.',
    )

    def fetch_events(self) -> list[SourceEvent]:
        raise RuntimeError('oauth token expired')


def test_connector_manifests_define_parallel_ingestion_contracts() -> None:
    manifests = {manifest.connector_type: manifest for manifest in list_connector_manifests()}

    assert manifests['slack'].auth_type == 'oauth'
    assert manifests['slack'].sync_strategy == 'incremental'
    assert 'channels:history' in manifests['slack'].required_scopes
    assert 'embed only changed' in manifests['slack'].cost_policy
    assert manifests['gmail'].auth_type == 'oauth'
    assert 'gmail.readonly' in manifests['gmail'].required_scopes
    assert get_connector_manifest('drive').display_name == 'Google Drive'


def test_sync_connector_events_records_job_and_ingests_review_items(db_session: Session) -> None:
    result = sync_connector_events(db=db_session, connector=ContractConnector())

    job = db_session.query(SyncJob).one()
    chunk = db_session.query(DocumentChunk).one()
    assert result.job_id == job.job_id
    assert result.connector_type == 'slack'
    assert result.status == 'complete'
    assert result.fetched_events == 1
    assert result.created_review_items == 1
    assert result.skipped_events == 0
    assert job.status == 'complete'
    assert job.message == 'fetched=1 created_review_items=1 skipped_events=0'
    assert job.progress_pct == 100
    assert chunk.metadata_['source_id'] == 'contract-event-1'
    assert chunk.metadata_['source_type'] == 'slack'
    assert chunk.metadata_['permission_level'] == 'internal'
    assert chunk.metadata_['participants'] == ['u123']
    assert chunk.metadata_['channel_id'] == 'C123'
    assert chunk.metadata_['external_updated_at'] == '2026-05-01T09:00:00+00:00'
    assert chunk.metadata_['ts'] == '1777600800.000100'


def test_sync_connector_events_reports_skipped_duplicates(db_session: Session) -> None:
    sync_connector_events(db=db_session, connector=ContractConnector())

    result = sync_connector_events(db=db_session, connector=ContractConnector())

    assert result.status == 'complete'
    assert result.fetched_events == 1
    assert result.created_review_items == 0
    assert result.skipped_events == 1


def test_sync_connector_events_passes_latest_slack_timestamp_cursor(db_session: Session) -> None:
    sync_connector_events(db=db_session, connector=ContractConnector())

    connector = IncrementalContractConnector()
    result = sync_connector_events(db=db_session, connector=connector)

    assert connector.observed_cursor == {'C123': '1777600800.000100'}
    assert result.fetched_events == 1
    assert result.created_review_items == 1


def test_sync_connector_events_passes_latest_generic_sync_cursor(db_session: Session) -> None:
    db_session.add(
        Source(
            source_type='gmail',
            source_id='gmail:older',
            source_url='https://mail.google.com/mail/u/0/#all/older',
            title='Older message',
            author='min@example.com',
            permission_level='internal',
            raw_metadata={'sync_partition': 'gmail', 'sync_cursor': '1777600800000'},
        )
    )
    db_session.add(
        Source(
            source_type='gmail',
            source_id='gmail:newer',
            source_url='https://mail.google.com/mail/u/0/#all/newer',
            title='Newer message',
            author='min@example.com',
            permission_level='internal',
            raw_metadata={'sync_partition': 'gmail', 'sync_cursor': '1777600900000'},
        )
    )
    db_session.commit()
    connector = IncrementalContractConnector(source_type='gmail')

    result = sync_connector_events(db=db_session, connector=connector)

    assert connector.observed_cursor == {'gmail': '1777600900000'}
    assert result.fetched_events == 1
    assert result.created_review_items == 1


def test_sync_connector_events_marks_job_failed_on_connector_error(db_session: Session) -> None:
    with pytest.raises(RuntimeError, match='oauth token expired'):
        sync_connector_events(db=db_session, connector=FailingConnector())

    job = db_session.query(SyncJob).one()
    assert job.connector_type == 'gmail'
    assert job.status == 'failed'
    assert job.message == 'failed: oauth token expired'
    assert job.progress_pct == 100
