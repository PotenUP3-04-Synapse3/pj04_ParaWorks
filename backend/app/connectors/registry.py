from backend.app.connectors.base import ConnectorManifest
from backend.app.connectors.mock import MOCK_CONNECTOR_MANIFESTS


def list_connector_manifests() -> list[ConnectorManifest]:
    return [MOCK_CONNECTOR_MANIFESTS[connector_type] for connector_type in sorted(MOCK_CONNECTOR_MANIFESTS)]


def get_connector_manifest(connector_type: str) -> ConnectorManifest:
    try:
        return MOCK_CONNECTOR_MANIFESTS[connector_type]
    except KeyError as exc:
        raise ValueError(f'Unsupported connector: {connector_type}') from exc
