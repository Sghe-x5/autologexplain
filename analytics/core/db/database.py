from typing import Any

import clickhouse_connect

from analytics.utils.config import (
    CLICKHOUSE_DATABASE,
    CLICKHOUSE_HOST,
    CLICKHOUSE_PASSWORD,
    CLICKHOUSE_PORT,
    CLICKHOUSE_USER,
)


def get_clickhouse_client() -> Any:
    try:
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=int(CLICKHOUSE_PORT),
            username=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            database=CLICKHOUSE_DATABASE,
        )
        client.ping()
        return client
    except Exception as e:
        print(f"{e}")
        raise
