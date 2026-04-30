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
