"""
Feature engineering для forecasting.

Для каждой точки (service, environment, minute_bucket) считаем 32 признака,
опирающихся на уже существующий pipeline:
  - log_signals_1m       — 1-минутные агрегаты по severity
  - slo_burn             — burn rates в окнах 5m/1h/6h
  - anomaly_events       — исторические аномалии (флаг «недавно была»)

Принцип: ничего нового не агрегируем в runtime. Берём то, что уже пишет
signals/engine.py и incidents/engine.py. Это даёт две важных property:
  1. Не дублируем вычисления.
  2. Фичи всегда согласованы с тем, что видит инцидент-детектор.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable, Mapping, Sequence

import numpy as np

# ─── Feature schema ─────────────────────────────────────────────────────────

FEATURE_NAMES: list[str] = [
    # Текущие counts (1 минута)
    "err_count_now",
    "warn_count_now",
    "total_count_now",
    "err_ratio_now",
    # Lag features — counts в прошлом (leading indicators)
    "err_lag_1m",
    "err_lag_3m",
    "err_lag_5m",
    "err_lag_10m",
    "warn_lag_3m",
    "warn_lag_5m",
    # Rolling статистика (5 минут)
    "err_mean_5m",
    "err_max_5m",
    "err_std_5m",
    "warn_mean_5m",
    # Rolling статистика (15 минут)
    "err_mean_15m",
    "err_max_15m",
    "err_sum_15m",
    "warn_mean_15m",
    # Rolling статистика (60 минут) — baseline
    "err_mean_60m",
    "err_std_60m",
    # Trend features
    "err_delta_1m",          # 1-й производная: current − previous
    "err_delta_5m",          # 1-я производная на 5-min window
    "err_accel_3m",          # 2-я производная: delta_now − delta_prev
    "err_ratio_to_60m",      # current / baseline_60m
    "warn_ratio_to_60m",
    "err_slope_5m",          # наклон линейной регрессии на 5-min window
    # SLO burn rates
    "burn_rate_5m",
    "burn_rate_1h",
    "burn_rate_6h",
    # Historical anomalies
    "anomalies_last_60m",
    # Календарные признаки
    "hour_of_day",
    "day_of_week",
]

FEATURE_COUNT = len(FEATURE_NAMES)

_WINDOW_SIZE_TO_MINUTES: dict[str, int] = {
    "5m": 5,
    "1h": 60,
    "6h": 360,
}


@dataclass
class FeaturePoint:
    """Одна точка обучающей выборки (service × minute)."""
    service: str
    environment: str
    minute: datetime
    features: np.ndarray  # shape (FEATURE_COUNT,)


# ─── Core builder ───────────────────────────────────────────────────────────


def build_feature_matrix(
    signal_rows: Iterable[Mapping],
    burn_rows: Iterable[Mapping] | None = None,
    anomaly_rows: Iterable[Mapping] | None = None,
) -> list[FeaturePoint]:
    """
    Построить фичи для всех (service, environment, minute_bucket) точек.

    Parameters
    ----------
    signal_rows : rows from log_signals_1m (dicts) — обязательный вход.
        Ожидаемые поля: service, environment, severity, minute_bucket, count.
    burn_rows : rows from slo_burn — опциональный вход.
        Ожидаемые поля: service, environment, window_start, window_size,
        error_budget_consumption.
    anomaly_rows : rows from anomaly_events — опциональный вход.
        Ожидаемые поля: service, environment, minute_bucket.

    Returns
    -------
    list[FeaturePoint]
    """
    # 1. Агрегируем signals по (service, env, minute) с разбивкой по severity
    by_key: dict[tuple[str, str, datetime], dict[str, int]] = defaultdict(
        lambda: {"error": 0, "warning": 0, "total": 0}
    )
    for r in signal_rows:
        svc = str(r.get("service") or "")
        env = str(r.get("environment") or "")
        minute = _parse_dt(r.get("minute_bucket"))
        if not svc or minute is None:
            continue
        severity = str(r.get("severity") or "").lower()
        count = int(r.get("count") or 0)
        if severity in {"error", "critical", "fatal"}:
            by_key[(svc, env, minute)]["error"] += count
        elif severity in {"warn", "warning"}:
            by_key[(svc, env, minute)]["warning"] += count
        by_key[(svc, env, minute)]["total"] += count

    # 2. SLO burn rates в map по minute END текущего окна:
    # для точки 12:00 burn(5m) берём из записи с window_start=11:55.
    burn_map: dict[tuple[str, str, datetime, str], float] = {}
    for r in burn_rows or []:
        svc = str(r.get("service") or "")
        env = str(r.get("environment") or "")
        ws = _parse_dt(r.get("window_start"))
        size = str(r.get("window_size") or "")
        if not svc or ws is None or size not in _WINDOW_SIZE_TO_MINUTES:
            continue
        val = float(r.get("error_budget_consumption") or 0)
        minute = (ws + timedelta(minutes=_WINDOW_SIZE_TO_MINUTES[size])).replace(
            second=0,
            microsecond=0,
        )
        burn_map[(svc, env, minute, size)] = val

    # 3. Anomaly events — set по (service, environment, minute).
    # Для старых callers без environment оставляем пустой env как wildcard.
    anomaly_minutes_by_dim: dict[tuple[str, str], set[datetime]] = defaultdict(set)
    for r in anomaly_rows or []:
        svc = str(r.get("service") or "")
        env = str(r.get("environment") or "")
        m = _parse_dt(r.get("minute_bucket"))
        if svc and m is not None:
            anomaly_minutes_by_dim[(svc, env)].add(m)

    # 4. Для каждого сервиса строим ordered list минут и считаем rolling stats
    points: list[FeaturePoint] = []
    by_service: dict[tuple[str, str], list[datetime]] = defaultdict(list)
    for (svc, env, minute) in by_key:
        by_service[(svc, env)].append(minute)
    for k in by_service:
        by_service[k].sort()

    for (svc, env), minutes in by_service.items():
        err_series = np.array(
            [by_key[(svc, env, m)]["error"] for m in minutes], dtype=float
        )
        warn_series = np.array(
            [by_key[(svc, env, m)]["warning"] for m in minutes], dtype=float
        )
        total_series = np.array(
            [by_key[(svc, env, m)]["total"] for m in minutes], dtype=float
        )

        for i, m in enumerate(minutes):
            feats = _point_features(
                idx=i,
                minutes=minutes,
                err=err_series,
                warn=warn_series,
                total=total_series,
                burn_map=burn_map,
                svc=svc,
                env=env,
                anomaly_minutes=(
                    anomaly_minutes_by_dim.get((svc, env), set())
                    | anomaly_minutes_by_dim.get((svc, ""), set())
                ),
            )
            points.append(FeaturePoint(svc, env, m, feats))

    return points


def _point_features(
    *,
    idx: int,
    minutes: list[datetime],
    err: np.ndarray,
    warn: np.ndarray,
    total: np.ndarray,
    burn_map: dict,
    svc: str,
    env: str,
    anomaly_minutes: set[datetime],
) -> np.ndarray:
    """Фичи для одной точки."""
    m = minutes[idx]
    err_now = float(err[idx])
    warn_now = float(warn[idx])
    total_now = float(total[idx])
    err_ratio_now = err_now / total_now if total_now > 0 else 0.0

    def err_window(n: int) -> np.ndarray:
        start = max(0, idx - n)
        return err[start:idx + 1]

    def warn_window(n: int) -> np.ndarray:
        start = max(0, idx - n)
        return warn[start:idx + 1]

    def lag(series: np.ndarray, k: int) -> float:
        return float(series[idx - k]) if idx - k >= 0 else 0.0

    # Lag features
    err_lag_1m = lag(err, 1)
    err_lag_3m = lag(err, 3)
    err_lag_5m = lag(err, 5)
    err_lag_10m = lag(err, 10)
    warn_lag_3m = lag(warn, 3)
    warn_lag_5m = lag(warn, 5)

    w5 = err_window(5)
    w15 = err_window(15)
    w60 = err_window(60)
    wW5 = warn_window(5)
    wW15 = warn_window(15)

    err_mean_5m = float(np.mean(w5)) if w5.size else 0.0
    err_max_5m = float(np.max(w5)) if w5.size else 0.0
    err_std_5m = float(np.std(w5)) if w5.size > 1 else 0.0
    warn_mean_5m = float(np.mean(wW5)) if wW5.size else 0.0
    err_mean_15m = float(np.mean(w15)) if w15.size else 0.0
    err_max_15m = float(np.max(w15)) if w15.size else 0.0
    err_sum_15m = float(np.sum(w15)) if w15.size else 0.0
    warn_mean_15m = float(np.mean(wW15)) if wW15.size else 0.0
    err_mean_60m = float(np.mean(w60)) if w60.size else 0.0
    err_std_60m = float(np.std(w60)) if w60.size > 1 else 0.0

    # Trend features
    err_delta_1m = err_now - err_lag_1m
    err_delta_5m = err_now - err_lag_5m
    # Acceleration: изменение delta (вторая производная)
    prev_delta = err_lag_1m - (float(err[idx - 2]) if idx >= 2 else 0.0)
    err_accel_3m = err_delta_1m - prev_delta

    err_ratio_60m = err_now / err_mean_60m if err_mean_60m > 0 else 0.0
    warn_ratio_60m = (
        warn_now / float(np.mean(warn_window(60))) if warn_window(60).size and np.mean(warn_window(60)) > 0 else 0.0
    )

    # Slope линейной регрессии: насколько растут counts в 5-мин окне
    if w5.size >= 2:
        xs = np.arange(w5.size, dtype=float)
        xm = xs.mean()
        ym = w5.mean()
        denom = float(np.sum((xs - xm) ** 2))
        slope = float(np.sum((xs - xm) * (w5 - ym)) / denom) if denom > 0 else 0.0
    else:
        slope = 0.0

    burn_5m = burn_map.get((svc, env, m, "5m"), 0.0)
    burn_1h = burn_map.get((svc, env, m, "1h"), 0.0)
    burn_6h = burn_map.get((svc, env, m, "6h"), 0.0)

    # anomalies in last 60m
    anomalies_60m = sum(
        1 for am in anomaly_minutes
        if am is not None and 0 < (m - am).total_seconds() <= 3600
    )

    return np.array(
        [
            err_now,
            warn_now,
            total_now,
            err_ratio_now,
            err_lag_1m,
            err_lag_3m,
            err_lag_5m,
            err_lag_10m,
            warn_lag_3m,
            warn_lag_5m,
            err_mean_5m,
            err_max_5m,
            err_std_5m,
            warn_mean_5m,
            err_mean_15m,
            err_max_15m,
            err_sum_15m,
            warn_mean_15m,
            err_mean_60m,
            err_std_60m,
            err_delta_1m,
            err_delta_5m,
            err_accel_3m,
            err_ratio_60m,
            warn_ratio_60m,
            slope,
            burn_5m,
            burn_1h,
            burn_6h,
            float(anomalies_60m),
            float(m.hour),
            float(m.weekday()),
        ],
        dtype=float,
    )


# ─── Utilities ──────────────────────────────────────────────────────────────


def _parse_dt(v) -> datetime | None:
    if v is None:
        return None
    if isinstance(v, datetime):
        return v.astimezone(timezone.utc) if v.tzinfo else v.replace(tzinfo=timezone.utc)
    if isinstance(v, str):
        try:
            # Handles both "YYYY-MM-DD HH:MM:SS" and ISO
            s = v.replace("T", " ")
            if "+" not in s and len(s) <= 19:
                return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)
            return datetime.fromisoformat(s)
        except Exception:
            return None
    return None


def features_as_dict(point: FeaturePoint) -> dict[str, float]:
    """Удобный способ посмотреть фичи точкой dict."""
    return dict(zip(FEATURE_NAMES, point.features.tolist(), strict=False))
