#!/usr/bin/env bash
# One-shot E2E reset: создать таблицу logs, залить seed, прогнать все pipeline циклы.
set -euo pipefail

cd "$(dirname "$0")"/..

echo "==> 1. Create logs table"
docker exec backend-clickhouse-1 clickhouse-client --query "
CREATE TABLE IF NOT EXISTS logs (
  timestamp DateTime64(3, 'UTC'),
  product LowCardinality(String),
  service LowCardinality(String),
  environment LowCardinality(String),
  level LowCardinality(String),
  status_code Int32 DEFAULT 0,
  trace_id String DEFAULT '',
  message String,
  metadata String DEFAULT '{}'
) ENGINE = MergeTree
PARTITION BY toDate(timestamp)
ORDER BY (service, environment, timestamp)
"

echo "==> 2. Regenerate synthetic logs"
python3 e2e-artifacts/seed_logs.py > /dev/null

echo "==> 3. Truncate logs and re-insert seed"
docker exec backend-clickhouse-1 clickhouse-client --query "TRUNCATE TABLE IF EXISTS logs"
docker cp e2e-artifacts/seed_logs.csv backend-clickhouse-1:/tmp/seed_logs.csv
docker exec backend-clickhouse-1 bash -c "clickhouse-client --query='INSERT INTO logs FORMAT CSVWithNames' < /tmp/seed_logs.csv"
echo -n "   logs count: "
docker exec backend-clickhouse-1 clickhouse-client --query "SELECT count() FROM logs"

echo "==> 4. Reset watermarks + truncate pipeline tables"
docker exec backend-redis-1 redis-cli DEL "signals:log_signals_1m:watermark" "signals:anomaly_events:watermark" > /dev/null
for t in log_signals_1m fingerprint_catalog anomaly_events incident_candidates incidents incident_events slo_burn service_dependency_graph; do
  docker exec backend-clickhouse-1 clickhouse-client --query "TRUNCATE TABLE $t" || true
done

echo "==> 5. Run signalization cycle"
docker exec backend-api-1 python -c "
from backend.services.signals import run_signalization_cycle
import json
result = run_signalization_cycle(initial_lookback_minutes=240, max_minutes_per_cycle=240, max_rows_per_minute=50000)
print('signalization:', json.dumps(result, default=str))
"

echo "==> 6. Run anomaly detection cycle"
docker exec backend-api-1 python -c "
from backend.services.signals import run_anomaly_detection_cycle
import json
result = run_anomaly_detection_cycle(
    initial_lookback_minutes=240, history_window_minutes=240, max_minutes_per_cycle=240,
    max_signals_per_minute=50000,
    volume_min_baseline_samples=5, volume_min_count=10, volume_ratio_threshold=3.0, volume_delta_threshold=10,
    new_fingerprint_min_count=10, new_fingerprint_max_history_total=3,
)
print('anomaly_detection:', json.dumps(result, default=str))
"

echo "==> 7. Run incident detector"
docker exec backend-api-1 python -c "
from backend.services.incidents import run_detector_cycle
import json
result = run_detector_cycle(lookback_minutes=360, max_logs=100000, anomaly_threshold=2.5, slo_target=0.995)
print('detector:', json.dumps(result, default=str))
"

echo "==> 8. Run incident correlator"
docker exec backend-api-1 python -c "
from backend.services.incidents import run_correlator_cycle
import json
result = run_correlator_cycle(lookback_minutes=360, max_candidates=500, merge_window_minutes=30, reopen_window_minutes=360)
print('correlator:', json.dumps(result, default=str))
"

echo "==> 9. Run incident RCA"
docker exec backend-api-1 python -c "
from backend.services.incidents import run_rca_cycle
import json
result = run_rca_cycle(max_incidents=200, trace_lookback_minutes=180)
print('rca:', json.dumps(result, default=str))
"

echo "==> 10. Quick sanity stats"
docker exec backend-clickhouse-1 clickhouse-client --query "
SELECT 'signals'  AS tbl, count() AS cnt FROM log_signals_1m UNION ALL
SELECT 'anomalies',           count() FROM anomaly_events UNION ALL
SELECT 'candidates',          count() FROM incident_candidates UNION ALL
SELECT 'incidents_snapshots', count() FROM incidents UNION ALL
SELECT 'incident_events',     count() FROM incident_events UNION ALL
SELECT 'slo_burn',             count() FROM slo_burn
FORMAT PrettyCompact
"

echo ""
echo "==> ✅ Pipeline ready. Frontend: http://localhost:5173 | API: http://localhost:8080"
