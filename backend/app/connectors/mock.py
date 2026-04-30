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
