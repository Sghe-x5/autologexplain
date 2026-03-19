from unittest.mock import patch

from backend.services.signals.schema import ensure_signal_tables


def test_ensure_signal_tables_executes_ddl(mock_ch_client):
    with patch("backend.services.signals.schema.client", return_value=mock_ch_client):
        ensure_signal_tables()

    assert mock_ch_client.command.call_count == 3
