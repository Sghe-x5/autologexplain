"""
Генератор тренировочного датасета для predictive incident forecasting.

В отличие от seed_logs.py (1 burst в последние 5 минут), здесь генерируется
**7 дней логов** с **~20 инцидентами** разных типов, разбросанных по времени.
Это нужно, чтобы обучить XGBoost-классификатор предсказывать инциденты
за 15 минут до их фактического начала.

На выходе:
  - e2e-artifacts/training_logs.csv      — ~500k логов
  - e2e-artifacts/training_labels.csv    — ground truth по (service, minute):
      - is_anomaly_now           (1 если это минута уже burst'а)
      - is_anomaly_in_15min      (1 если через 15 минут начнётся burst)
      - is_anomaly_in_30min      (1 если через 30 минут)

Типы инцидентов (симулируются разнообразные причины):
  1. db_timeout         — postgres-writer errors, затем cascade в payments-api → notifications
  2. oom                — резкий рост error в одном сервисе, без cascade
  3. network            — warn/error в auth-gateway и frontend-app одновременно
  4. slow_degradation   — постепенный рост error rate (важно для forecasting!)
  5. noisy_neighbor     — фоновый шум, не должен классифицироваться как инцидент
"""

import csv
import json
import random
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

random.seed(1337)

NOW = datetime.now(timezone.utc).replace(microsecond=0, second=0)
DAYS_BACK = 7

ART = Path(__file__).resolve().parent
LOGS_CSV = ART / "training_logs.csv"
LABELS_CSV = ART / "training_labels.csv"

SERVICES = [
    ("maps", "auth-gateway",     "backend"),
    ("maps", "payments-api",     "backend"),
    ("maps", "postgres-writer",  "database"),
    ("maps", "notifications",    "backend"),
    ("maps", "frontend-app",     "frontend"),
    ("maps", "cdn-proxy",        "infrastructure"),
]

ROWS = []
INCIDENTS: list[dict] = []  # Список всех запланированных burst-окон


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


# ─── Baseline traffic (7 дней × 24 часа × 60 минут × ~8 логов/мин/сервис) ─────

def gen_baseline():
    for minute_offset in range(DAYS_BACK * 24 * 60, 0, -1):
        t = NOW - timedelta(minutes=minute_offset)

        # Часовая зависимость нагрузки (day/night)
        hour = t.hour
        if 9 <= hour <= 22:
            load_mult = 1.0  # day
        else:
            load_mult = 0.4  # night

        for product, service, layer_hint in SERVICES:
            n = max(1, int(random.randint(3, 8) * load_mult))
            for _ in range(n):
                ts = t + timedelta(seconds=random.randint(0, 59))
                trace_id = uuid.uuid4().hex
                r = random.random()
                if r < 0.005:  # редкие warns
                    emit(ts, product, service, "prod", "warn", 200, trace_id,
                         f"slow response detected for request {random.randint(1, 99999)}")
                elif r < 0.002 + 0.005:  # редкие transient errors (noise для baseline)
                    emit(ts, product, service, "prod", "error", 500, trace_id,
                         f"transient error: retry attempt {random.randint(1, 3)}")
                else:
                    msg_pool = [
                        f"request handled in {random.randint(5, 80)}ms",
                        f"cache hit for key user_{random.randint(1, 5000)}",
                        f"processed batch of {random.randint(1, 50)} items",
                        f"health check ok",
                    ]
                    emit(ts, product, service, "prod", "info", 200, trace_id,
                         random.choice(msg_pool))


# ─── Incidents: 4 типа, разбросаны по времени ───────────────────────────────

def schedule_incident(center_minute: int, kind: str, primary_service: str,
                      duration_min: int = 5, build_up_min: int = 0):
    """
    Планирует burst:
      - center_minute:  minute offset от NOW (как давно произошло)
      - kind:           тип инцидента (для метрики)
      - duration_min:   длительность burst-окна
      - build_up_min:   длительность предварительной фазы (постепенный рост —
                         forecasting должен научиться ловить именно это)
    """
    INCIDENTS.append({
        "kind": kind,
        "primary_service": primary_service,
        "center_minute_offset": center_minute,
        "duration_min": duration_min,
        "build_up_min": build_up_min,
    })


def emit_incident(inc: dict):
    """Генерирует логи для одного запланированного инцидента."""
    svc = inc["primary_service"]
    center = inc["center_minute_offset"]
    dur = inc["duration_min"]
    bu = inc["build_up_min"]
    kind = inc["kind"]

    # Build-up phase: realistic precursor-сигналы. Exponential-growth curve
    # создаёт чёткую «сигнатуру предвестника»:
    #   - первые минуты precursor-фазы: едва заметные warn-логи
    #   - последние 5 минут перед burst'ом: уже значительный рост error-логов
    # Это imitrует реальные production-предвестники (replay storms, GC pressure
    # before OOM, connection-pool saturation before DB timeouts).
    for minute in range(center + dur + bu, center + dur, -1):
        t = NOW - timedelta(minutes=minute)
        # phase ∈ [0, 1]: 0 = начало precursor'а (далеко от burst'а),
        #                 1 = самый конец precursor'а (burst начнётся через 1 мин)
        phase = (center + dur + bu - minute) / max(bu, 1)
        # Exponential growth: в начале очень мало, в конце — сильно
        intensity = phase ** 1.5
        # error count растёт с 3 до ~40 (что становится явным leading signal)
        err_count = int(3 + 40 * intensity + random.randint(0, 5))
        # warn count — тоже exponential
        warn_count = int(5 + 30 * intensity + random.randint(0, 3))
        for _ in range(err_count):
            ts = t + timedelta(seconds=random.randint(0, 59))
            _emit_incident_log(ts, svc, kind)
        for _ in range(warn_count):
            ts = t + timedelta(seconds=random.randint(0, 59))
            tid = uuid.uuid4().hex
            emit(ts, "maps", svc, "prod", "warn", 200, tid,
                 f"slow response detected: p99 latency {random.randint(500, 3000)}ms")

    # Main burst (acute phase)
    for minute in range(center + dur, center, -1):
        t = NOW - timedelta(minutes=minute)
        burst = random.randint(50, 90)
        for _ in range(burst):
            ts = t + timedelta(seconds=random.randint(0, 59))
            _emit_incident_log(ts, svc, kind)

        # Cascade behavior
        if kind == "db_timeout" and minute <= center + dur - 1:
            for _ in range(random.randint(20, 40)):
                ts = t + timedelta(seconds=random.randint(1, 50))
                tid = uuid.uuid4().hex
                emit(ts, "maps", "payments-api", "prod", "error", 503, tid,
                     f"downstream db call failed for tx_{random.randint(1000, 99999)}")

        if kind == "db_timeout" and minute <= center + dur - 2:
            for _ in range(random.randint(15, 30)):
                ts = t + timedelta(seconds=random.randint(1, 50))
                tid = uuid.uuid4().hex
                emit(ts, "maps", "notifications", "prod", "error", 503, tid,
                     f"failed to send notification for user {random.randint(1, 9999)}: upstream unavailable")

        if kind == "network":
            for other in ["frontend-app"]:
                for _ in range(random.randint(10, 25)):
                    ts = t + timedelta(seconds=random.randint(1, 50))
                    tid = uuid.uuid4().hex
                    emit(ts, "maps", other, "prod", "warn", 502, tid,
                         f"upstream timeout after {random.randint(1000, 5000)}ms")


def _emit_incident_log(ts, svc, kind):
    tid = uuid.uuid4().hex
    if kind == "db_timeout":
        emit(ts, "maps", svc, "prod", "error", 500, tid,
             f"db query failed: timeout after {random.choice([50, 100, 200, 500])}ms on connection pool",
             meta={"category": "database"})
    elif kind == "oom":
        emit(ts, "maps", svc, "prod", "critical", 500, tid,
             f"OutOfMemoryError: Java heap space at worker {random.randint(1, 8)}")
    elif kind == "network":
        emit(ts, "maps", svc, "prod", "error", 504, tid,
             f"gateway timeout: upstream {random.choice(['auth', 'profile', 'geo'])} not responding within {random.randint(3, 15)}s")
    elif kind == "slow_degradation":
        emit(ts, "maps", svc, "prod", "error", 500, tid,
             f"request failed with status 500: internal_error on endpoint /api/v1/{random.choice(['tiles', 'search', 'routes'])}/")


# Сгенерируем ~40 инцидентов по всем 7 дням.
# КАЖДЫЙ инцидент имеет достаточно длинный precursor (≥12 мин), т.к. в
# реальности перед любым burst'ом есть лead-indicators: growth в retry
# counts, slow queries, latency deg-ы. Это делает задачу forecasting
# решаемой с хорошим lead-time.
def schedule_all_incidents():
    types = [
        ("db_timeout", "postgres-writer", 5, 18),
        ("db_timeout", "postgres-writer", 7, 15),
        ("db_timeout", "postgres-writer", 6, 20),
        ("db_timeout", "postgres-writer", 8, 12),
        ("db_timeout", "postgres-writer", 5, 25),
        ("db_timeout", "postgres-writer", 7, 18),
        ("db_timeout", "postgres-writer", 6, 15),
        ("db_timeout", "postgres-writer", 5, 20),
        ("oom", "payments-api", 4, 20),
        ("oom", "auth-gateway", 3, 15),
        ("oom", "notifications", 3, 18),
        ("oom", "payments-api", 4, 22),
        ("oom", "auth-gateway", 3, 20),
        ("oom", "payments-api", 5, 15),
        ("network", "auth-gateway", 6, 18),
        ("network", "cdn-proxy", 8, 15),
        ("network", "frontend-app", 7, 20),
        ("network", "cdn-proxy", 5, 12),
        ("network", "auth-gateway", 5, 15),
        ("network", "frontend-app", 6, 18),
        ("network", "cdn-proxy", 7, 20),
        ("slow_degradation", "payments-api", 5, 25),
        ("slow_degradation", "postgres-writer", 6, 30),
        ("slow_degradation", "notifications", 4, 20),
        ("slow_degradation", "auth-gateway", 5, 30),
        ("slow_degradation", "payments-api", 4, 25),
        ("slow_degradation", "notifications", 6, 30),
        ("slow_degradation", "cdn-proxy", 5, 25),
        ("slow_degradation", "postgres-writer", 5, 20),
        ("slow_degradation", "frontend-app", 5, 22),
        ("db_timeout", "postgres-writer", 6, 15),
        ("oom", "notifications", 4, 12),
        ("network", "auth-gateway", 4, 15),
        ("slow_degradation", "payments-api", 6, 25),
        ("db_timeout", "postgres-writer", 7, 18),
        ("oom", "auth-gateway", 4, 15),
        ("network", "frontend-app", 5, 20),
        ("slow_degradation", "cdn-proxy", 4, 20),
        ("db_timeout", "postgres-writer", 5, 15),
        ("oom", "payments-api", 3, 18),
    ]

    # Равномерно распределить по 7 дням (с запасом, чтобы не было overlap)
    total_minutes = DAYS_BACK * 24 * 60
    random.shuffle(types)
    used_windows: list[tuple[int, int]] = []
    for kind, svc, dur, bu in types:
        # Выбираем центр
        attempts = 0
        while attempts < 50:
            center = random.randint(120, total_minutes - 120)  # отступ от краёв
            # Проверяем overlap (±60 минут)
            if any(abs(center - c) < (max(dur, bu) + 60) for c, _ in used_windows):
                attempts += 1
                continue
            used_windows.append((center, dur + bu))
            schedule_incident(center, kind, svc, dur, bu)
            break


# ─── Labels: для каждого (service, minute) — метка на 0/15/30 минут вперёд ──

def build_labels():
    """
    Для каждого (service, minute) в наших логах строим:
      - is_anomaly_now:       этот (svc, min) попадает в burst
      - is_anomaly_in_15min:  через 15 минут начнётся burst по этому сервису
      - is_anomaly_in_30min:  через 30 минут начнётся burst
    """
    # Строим множество (service, minute_offset) попадающих в burst
    burst_windows: set[tuple[str, int]] = set()  # (service, minute_offset)
    cascade_windows: set[tuple[str, int]] = set()  # cascade-сервисы тоже считаются аномалией
    build_up_windows: set[tuple[str, int]] = set()  # build-up фаза

    for inc in INCIDENTS:
        svc = inc["primary_service"]
        center = inc["center_minute_offset"]
        dur = inc["duration_min"]
        bu = inc["build_up_min"]
        kind = inc["kind"]

        # Acute phase
        for m in range(center + 1, center + dur + 1):
            burst_windows.add((svc, m))

        # Build-up phase
        for m in range(center + dur + 1, center + dur + bu + 1):
            build_up_windows.add((svc, m))

        # Cascade
        if kind == "db_timeout":
            for m in range(center + 1, center + dur):
                cascade_windows.add(("payments-api", m))
                cascade_windows.add(("notifications", m))
        if kind == "network":
            for m in range(center + 1, center + dur + 1):
                cascade_windows.add(("frontend-app", m))

    # Соберём все (service, minute_offset) встречающиеся в данных
    all_keys: set[tuple[str, int]] = set()
    for r in ROWS:
        dt = datetime.strptime(r["timestamp"][:16], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc)
        minute_offset = int((NOW - dt).total_seconds() // 60)
        all_keys.add((r["service"], minute_offset))

    any_burst = burst_windows | cascade_windows | build_up_windows

    # Запишем labels CSV
    with LABELS_CSV.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow([
            "service", "minute_offset", "minute_utc",
            "is_anomaly_now", "is_anomaly_in_15min", "is_anomaly_in_30min",
            "incident_kind",
        ])
        for (svc, mo) in sorted(all_keys):
            # is_anomaly_now
            is_now = 1 if (svc, mo) in any_burst else 0
            # is_anomaly_in_15min: в ближайшие 15 минут (1-15 вперёд) будет хоть одна аномалия
            is_15 = 0
            for future in range(1, 16):
                if (svc, mo - future) in any_burst:  # mo - future = более свежая минута
                    is_15 = 1
                    break
            is_30 = 0
            for future in range(1, 31):
                if (svc, mo - future) in any_burst:
                    is_30 = 1
                    break

            # Какой тип инцидента (для аналитики)
            kind = ""
            if is_now:
                for inc in INCIDENTS:
                    if inc["primary_service"] == svc:
                        c = inc["center_minute_offset"]
                        d = inc["duration_min"]
                        b = inc["build_up_min"]
                        if c < mo <= c + d + b:
                            kind = inc["kind"]
                            break

            minute_utc = (NOW - timedelta(minutes=mo)).strftime("%Y-%m-%d %H:%M")
            w.writerow([svc, mo, minute_utc, is_now, is_15, is_30, kind])

    return len(all_keys), sum(1 for k in all_keys if k in any_burst)


# ─── Main ──────────────────────────────────────────────────────────────────

def main():
    print("Generating baseline traffic (7 days × 6 services × ~8 logs/min)...")
    gen_baseline()
    print(f"  baseline rows: {len(ROWS)}")

    print("\nScheduling incidents...")
    schedule_all_incidents()
    print(f"  scheduled: {len(INCIDENTS)} incidents")
    for inc in INCIDENTS[:5]:
        print(f"    - {inc['kind']:20} svc={inc['primary_service']:18} "
              f"center=T-{inc['center_minute_offset']}m  dur={inc['duration_min']}m  build_up={inc['build_up_min']}m")
    print(f"    ... ({len(INCIDENTS) - 5} more)")

    print("\nEmitting incident logs...")
    n_before = len(ROWS)
    for inc in INCIDENTS:
        emit_incident(inc)
    print(f"  incident rows: {len(ROWS) - n_before}")

    print(f"\nTotal rows: {len(ROWS)}")

    # Отсортируем по timestamp для удобства
    ROWS.sort(key=lambda r: r["timestamp"])

    # Записываем logs CSV
    print(f"\nWriting {LOGS_CSV}...")
    with LOGS_CSV.open("w", newline="") as f:
        w = csv.writer(f, quoting=csv.QUOTE_ALL)
        w.writerow(["timestamp", "product", "service", "environment", "level",
                    "status_code", "trace_id", "message", "metadata"])
        for r in ROWS:
            w.writerow([r["timestamp"], r["product"], r["service"], r["environment"],
                        r["level"], r["status_code"], r["trace_id"], r["message"], r["metadata"]])

    print(f"Writing {LABELS_CSV}...")
    total_windows, positive_windows = build_labels()

    print(f"\n=== Summary ===")
    print(f"  Total (service, minute) windows: {total_windows}")
    print(f"  Positive (in burst):             {positive_windows}")
    print(f"  Negative (baseline):             {total_windows - positive_windows}")
    print(f"  Incidents scheduled:             {len(INCIDENTS)}")


if __name__ == "__main__":
    main()
