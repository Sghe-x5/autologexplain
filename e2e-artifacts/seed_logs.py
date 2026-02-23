"""
Синтетические логи для E2E-теста.

Сценарий каскада:
- 4 сервиса: auth-gateway → payments-api → postgres-writer → notifications
- 120 минут нормального трафика (низкая частота, info + иногда warn)
- За 5 минут до now: внезапный всплеск errors в postgres-writer (root cause)
- За 3 минуты до now: каскад ошибок в payments-api (downstream)
- За 1 минуту до now: каскад в notifications и auth-gateway

Ожидание:
- anomaly_detector найдёт volume_spike в postgres-writer + payments-api + notifications
- incident_manager построит инцидент c fingerprint по шаблону "db query failed: timeout after <num>"
- RCA определит root_cause_service = postgres-writer (earliest + downstream fanout)
"""

import csv
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(42)

NOW = datetime.now(timezone.utc).replace(microsecond=0)
BASELINE_START = NOW - timedelta(minutes=180)
ART = Path(__file__).resolve().parent

ROWS = []


def emit(ts, product, service, environment, level, status, trace_id, message, meta=None):
    ROWS.append({
        "timestamp": ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
        "product": product,
        "service": service,
        "environment": environment,
        "level": level,
        "status_code": status,
        "trace_id": trace_id,
        "message": message,
        "metadata": json.dumps(meta or {}),
    })


SERVICES_NORMAL = [
    ("maps", "auth-gateway", "backend"),
    ("maps", "payments-api", "backend"),
    ("maps", "postgres-writer", "database"),
    ("maps", "notifications", "backend"),
    ("maps", "frontend-app", "frontend"),
]

# --- Baseline: 180 минут нормального трафика ---
for minute in range(180, 5, -1):
    t = NOW - timedelta(minutes=minute)
    for (product, service, layer_hint) in SERVICES_NORMAL:
        n = random.randint(2, 6)
        for _ in range(n):
            ts = t + timedelta(seconds=random.randint(0, 59))
            trace_id = uuid.uuid4().hex
            if random.random() < 0.02:
                emit(ts, product, service, "prod", "warn", 200, trace_id,
                     f"slow response detected for request {random.randint(1, 9999)}")
            else:
                msg_pool = [
                    f"request handled in {random.randint(5, 80)}ms",
                    f"cache hit for key user_{random.randint(1, 5000)}",
                    f"processed batch of {random.randint(1, 50)} items",
                ]
                emit(ts, product, service, "prod", "info", 200, trace_id, random.choice(msg_pool))

# --- BASELINE NOISE: случайные transient-ошибки раз в ~20 минут в произвольных
#     сервисах. Это реалистичный production-шум: короткая деградация, retry,
#     быстрое восстановление. Classic z-score должен от этого «засоряться»
#     (std раздувается → сложнее отличить burst от noise).
#     НЕ помечаются как ground-truth (это не наши целевые аномалии).
NOISY_SERVICES = ["auth-gateway", "payments-api", "notifications", "postgres-writer"]
for _ in range(25):
    minute = random.randint(10, 175)  # не трогаем burst-окно (<=5 мин)
    t = NOW - timedelta(minutes=minute)
    svc = random.choice(NOISY_SERVICES)
    noise_count = random.randint(8, 22)
    for _ in range(noise_count):
        ts = t + timedelta(seconds=random.randint(0, 59))
        trace_id = uuid.uuid4().hex
        emit(
            ts, "maps", svc, "prod", "error", 500, trace_id,
            f"transient error: retry attempt {random.randint(1, 3)} of 3",
        )

# --- ANOMALY: burst of DB errors in last 5 minutes ---
# T-5 to T-0 минут — волна ошибок в postgres-writer (root cause)
for minute in range(5, 0, -1):
    t = NOW - timedelta(minutes=minute)
    burst = 80 if minute >= 3 else 60
    for i in range(burst):
        ts = t + timedelta(seconds=random.randint(0, 59))
        trace_id = uuid.uuid4().hex
        emit(ts, "maps", "postgres-writer", "prod", "error", 500, trace_id,
             f"db query failed: timeout after {random.choice([50, 100, 200])}ms on connection pool",
             meta={"category": "database"})

        # Cascade: payments-api depends on postgres — появляется через 1 минуту
        if minute <= 4:
            emit(ts + timedelta(seconds=random.randint(1, 30)), "maps", "payments-api", "prod",
                 "error", 503, trace_id,
                 f"downstream db call failed for tx_{random.randint(1000, 9999)}")

        # Cascade в notifications — через 2 минуты
        if minute <= 3:
            emit(ts + timedelta(seconds=random.randint(2, 40)), "maps", "notifications", "prod",
                 "error", 503, trace_id,
                 f"failed to send notification for user {random.randint(1, 1000)}: upstream unavailable")

# --- Sprinkle одного непрерывного trace-id через все 4 сервиса для графа ---
for _ in range(150):
    trace_id = uuid.uuid4().hex
    t = NOW - timedelta(minutes=random.randint(10, 120))
    for i, (p, s, _) in enumerate(SERVICES_NORMAL[:4]):
        emit(t + timedelta(seconds=i * 2), p, s, "prod", "info", 200, trace_id,
             f"trace hop through {s}")

# Запишем в CSV для ClickHouse
csv_path = ART / "seed_logs.csv"
with csv_path.open("w", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(["timestamp", "product", "service", "environment", "level", "status_code", "trace_id", "message", "metadata"])
    for r in ROWS:
        w.writerow([r["timestamp"], r["product"], r["service"], r["environment"], r["level"],
                    r["status_code"], r["trace_id"], r["message"], r["metadata"]])

print(f"Generated {len(ROWS)} log records")
print(f"CSV: {csv_path}")
print(f"Time range: {ROWS[0]['timestamp']} … {ROWS[-1]['timestamp']}")

# --- Ground-truth labels для ML-метрик ---
# Для каждого (минута, сервис) заводим бинарную метку is_anomaly.
# Положительные (ground truth): окна, в которые мы ВСТАВИЛИ burst.
#   - postgres-writer: минуты T-5..T-1 (5 минут)
#   - payments-api:    минуты T-4..T-1 (4 минуты)
#   - notifications:   минуты T-3..T-1 (3 минуты)
# Остальные (service, minute) — негативы.

anomaly_windows: dict[tuple[str, str], int] = {}

def minute_key(ts_iso: str) -> str:
    # ts_iso: "YYYY-MM-DD HH:MM:SS.mmm" → "YYYY-MM-DD HH:MM"
    return ts_iso[:16]

# Перечень (service, minute) в которых мы НАМЕРЕННО вставляли аномалию.
positive_set: set[tuple[str, str]] = set()
for minute in range(5, 0, -1):
    m = (NOW - timedelta(minutes=minute)).strftime("%Y-%m-%d %H:%M")
    positive_set.add(("postgres-writer", m))
    if minute <= 4:
        positive_set.add(("payments-api", m))
    if minute <= 3:
        positive_set.add(("notifications", m))

# Соберём все (service, minute), которые вообще встречаются в логах.
all_keys: set[tuple[str, str]] = set()
for r in ROWS:
    all_keys.add((r["service"], minute_key(r["timestamp"])))

labels_path = ART / "seed_labels.csv"
with labels_path.open("w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["service", "minute", "is_anomaly"])
    for (svc, m) in sorted(all_keys):
        w.writerow([svc, m, 1 if (svc, m) in positive_set else 0])

print(f"\nLabels: {labels_path}")
print(f"  positives (ground-truth anomalies): {len(positive_set)}")
print(f"  negatives (baseline windows):       {len(all_keys) - len(positive_set)}")
print(f"  total windows labeled:              {len(all_keys)}")

# Статистика по сервисам
from collections import Counter
by_service = Counter((r["service"], r["level"]) for r in ROWS)
print()
for (svc, lvl), cnt in sorted(by_service.items()):
    print(f"  {svc:20s} {lvl:10s} {cnt}")
