import clickhouse_connect
from utils.config import (
    CLICKHOUSE_HOST, CLICKHOUSE_PORT, CLICKHOUSE_USER, 
    CLICKHOUSE_PASSWORD, CLICKHOUSE_DATABASE
)

def get_clickhouse_client():
    try:
        client = clickhouse_connect.get_client(
            host=CLICKHOUSE_HOST,
            port=int(CLICKHOUSE_PORT),
            username=CLICKHOUSE_USER,
            password=CLICKHOUSE_PASSWORD,
            database=CLICKHOUSE_DATABASE
        )
        client.ping()
        return client
    except Exception as e:
        print(f"{e}")
        raise
