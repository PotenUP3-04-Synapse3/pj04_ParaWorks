import copy
from dataclasses import dataclass

from backend.app.connectors.base import ConnectorManifest, SourceEvent
from backend.app.seeds.mock_sources import SEED_EVENTS

CONNECTOR_TYPES = {'drive', 'gmail', 'slack', 'calendar'}

MOCK_CONNECTOR_MANIFESTS: dict[str, ConnectorManifest] = {
    'calendar': ConnectorManifest(
        connector_type='calendar',
        display_name='Google Calendar',
        mode='mock',
        auth_type='oauth',
        required_scopes=('calendar.readonly',),
        sync_strategy='incremental',
        cost_policy='Fetch event deltas before extracting review candidates.',
    ),
    'drive': ConnectorManifest(
        connector_type='drive',
        display_name='Google Drive',
        mode='mock',
        auth_type='oauth',
        required_scopes=('drive.readonly',),
        sync_strategy='incremental',
        cost_policy='Fetch changed files first; embed approved chunks only after hash checks.',
    ),
    'gmail': ConnectorManifest(
        connector_type='gmail',
        display_name='Gmail',
        mode='mock',
        auth_type='oauth',
        required_scopes=('gmail.readonly',),
        sync_strategy='incremental',
        cost_policy='Fetch message deltas before review extraction.',
    ),
    'slack': ConnectorManifest(
        connector_type='slack',
        display_name='Slack',
        mode='mock',
        auth_type='oauth',
        required_scopes=('channels:history', 'groups:history', 'im:history', 'mpim:history'),
        sync_strategy='incremental',
        cost_policy='Fetch source deltas first; embed only changed chunks after review approval.',
    ),
}


@dataclass(frozen=True)
class MockConnector:
    source_type: str

    @property
    def manifest(self) -> ConnectorManifest:
        return MOCK_CONNECTOR_MANIFESTS[self.source_type]

    def fetch_events(self) -> list[SourceEvent]:
        source_types = {self.source_type}
        if self.source_type == 'gmail':
            source_types.add('gmail_attachment')
        return [copy.deepcopy(event) for event in SEED_EVENTS if event.source_type in source_types]


def get_mock_connector(source_type: str) -> MockConnector:
    if source_type not in CONNECTOR_TYPES:
        raise ValueError(f'Unsupported mock connector: {source_type}')
    return MockConnector(source_type)
