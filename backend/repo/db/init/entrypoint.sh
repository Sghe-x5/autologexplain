# db/init/entrypoint.sh
#!/usr/bin/env bash
set -euo pipefail
shopt -s nullglob

HOST="${CLICKHOUSE_HOST:-clickhouse}"
PORT="${CLICKHOUSE_PORT:-9000}"
USER="${CLICKHOUSE_USER:-app}"
PASS="${CLICKHOUSE_PASSWORD:-app_pass}"

echo "Waiting for ClickHouse at ${HOST}:${PORT}..."
for i in {1..60}; do
  if clickhouse-client --host="$HOST" --port="$PORT" --user="$USER" --password="$PASS" -q "SELECT 1" >/dev/null 2>&1; then
    echo "ClickHouse is ready."
    break
  fi
  echo "  not ready yet ($i/60), retrying in 1s..."
  sleep 1
done

# Схема через .sql
for f in /init/*.sql; do
  [[ "$(basename "$f")" == "02_load_csv.sql" ]] && continue  # пропустим CSV-запрос, он нам не нужен
  echo "Applying $f"
  clickhouse-client --host="$HOST" --port="$PORT" --user="$USER" --password="$PASS" --multiquery < "$f"
done

# Загрузка CSV через stdin
if [[ -f /data/logs_sample.csv ]]; then
  echo "Loading CSV..."
  clickhouse-client --host="$HOST" --port="$PORT" --user="$USER" --password="$PASS" \
    --query="INSERT INTO logs FORMAT CSVWithNames" < /data/logs_sample.csv
  echo "CSV loaded."
else
  echo "WARNING: /data/logs_sample.csv not found, skipping load."
fi

echo "Init done."