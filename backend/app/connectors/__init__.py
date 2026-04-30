from backend.app.connectors.base import Connector, SourceEvent


def get_mock_connector(source_type: str):
    from backend.app.connectors.mock import get_mock_connector as _get_mock_connector

    return _get_mock_connector(source_type)

__all__ = ['Connector', 'SourceEvent', 'get_mock_connector']
