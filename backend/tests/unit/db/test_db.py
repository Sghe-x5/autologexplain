from unittest.mock import patch, Mock
from db.db import query, ping, _normalize_json_columns


def test_ping_success(mock_ch_client):
    """Тест проверки доступности ClickHouse"""
    with patch("db.db.client", return_value=mock_ch_client):
        assert ping() is True
        mock_ch_client.ping.assert_called_once()


def test_ping_failure(mock_ch_client):
    """Тест недоступности ClickHouse"""
    mock_ch_client.ping.side_effect = Exception("Connection failed")
    with patch("db.db.client", return_value=mock_ch_client):
        assert ping() is False


def test_normalize_json_columns():
    """Тест преобразования JSON-колонок"""
    test_data = [
        {"metadata": '{"key": "value"}'},
        {"metadata": b'{"key": "bytes"}'},
        {"metadata": "invalid_json"},
        {"other": "data"},
    ]

    result = _normalize_json_columns(test_data)

    assert result[0]["metadata"] == {"key": "value"}
    assert result[1]["metadata"] == {"key": "bytes"}
    assert result[2]["metadata"] == {}
    assert "other" in result[3]


def test_query(mock_ch_client):
    """Тест выполнения запроса"""
    mock_result = Mock()
    mock_result.column_names = ["id", "name"]
    mock_result.result_rows = [(1, "test"), (2, "data")]
    mock_ch_client.query.return_value = mock_result

    with patch("db.db.client", return_value=mock_ch_client):
        rows = query("SELECT * FROM table")

        assert len(rows) == 2
        assert rows[0]["id"] == 1
        mock_ch_client.query.assert_called_once()
