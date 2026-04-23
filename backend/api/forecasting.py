"""
Forecasting API (Variant Y Lite).

Endpoints:
  GET  /forecasting/risk        — risk score для каждого (service, env) на last minute
  POST /forecasting/explain     — SHAP объяснение для одной точки
  GET  /forecasting/info        — метаданные модели (metrics, features, size)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from loguru import logger

from backend.core.config import get_settings
from backend.db.db import query as ch_query
from backend.services.forecasting import (
    FEATURE_NAMES,
    IncidentForecaster,
    build_feature_matrix,
    explain_prediction,
)

router = APIRouter(prefix="/forecasting", tags=["forecasting"])

_forecaster: IncidentForecaster | None = None


def _get_forecaster() -> IncidentForecaster:
    global _forecaster
    if _forecaster is None:
        _forecaster = IncidentForecaster()
    return _forecaster


@router.get("/info")
def forecaster_info():
    """Возвращает метаданные модели и качество на test-split."""
    metrics_path = Path("/app/backend/services/forecasting/models/forecaster_metrics.json")
    if not metrics_path.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                "forecaster_not_trained: run "
                "`docker exec backend-api-1 python -m backend.services.forecasting.trainer`"
            ),
        )
    return json.loads(metrics_path.read_text())


@router.get("/risk")
def current_risk(hours: int = Query(default=2, ge=1, le=24)):
    """
    Предсказать риск инцидента в ближайшие 15 минут для каждого сервиса
    на основе последних hours часов signals.

    Читает log_signals_1m + slo_burn + anomaly_events из ClickHouse,
    строит features для ПОСЛЕДНЕЙ минуты каждого (service, env), запрашивает модель.
    """
    fc = _get_forecaster()
    try:
        fc.get_booster()  # ensure loaded
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"forecasting_dependency_missing:{exc.name}",
        ) from exc

    try:
        signal_rows = ch_query(
            """
            SELECT service, environment, severity, minute_bucket, sum(count) AS count
            FROM log_signals_1m
            WHERE minute_bucket >= now() - INTERVAL %(h)s HOUR
            GROUP BY service, environment, severity, minute_bucket
            ORDER BY minute_bucket
            """,
            {"h": hours},
            json_columns=[],
        )
    except Exception as exc:
        logger.exception("forecasting: clickhouse error (signals)")
        raise HTTPException(status_code=500, detail="failed_to_fetch_signals") from exc

    # Optional — burn & anomalies
    try:
        burn_rows = ch_query(
            """
            SELECT service, environment, window_size, window_start,
                   error_budget_consumption
            FROM slo_burn
            WHERE window_start >= now() - INTERVAL %(h)s HOUR
            """,
            {"h": hours},
            json_columns=[],
        )
    except Exception:
        burn_rows = []

    try:
        anomaly_rows = ch_query(
            """
            SELECT service, environment, minute_bucket
            FROM anomaly_events
            WHERE minute_bucket >= now() - INTERVAL %(h)s HOUR
            """,
            {"h": hours},
            json_columns=[],
        )
    except Exception:
        anomaly_rows = []

    points = build_feature_matrix(signal_rows, burn_rows, anomaly_rows)
    if not points:
        return {"predictions": [], "horizon_minutes": 15}

    # Только последнюю минуту каждого (service, env)
    latest: dict[tuple[str, str], Any] = {}
    for p in points:
        key = (p.service, p.environment)
        if key not in latest or p.minute > latest[key].minute:
            latest[key] = p
    latest_points = list(latest.values())

    try:
        probs = fc.predict_proba(latest_points)
        explanations = explain_prediction(fc, latest_points, probs, top_n=5)
    except ModuleNotFoundError as exc:
        raise HTTPException(
            status_code=500,
            detail=f"forecasting_dependency_missing:{exc.name}",
        ) from exc

    results = []
    for p, prob, expl in zip(latest_points, probs, explanations, strict=True):
        results.append(
            {
                "service": p.service,
                "environment": p.environment,
                "minute": p.minute.isoformat(timespec="seconds"),
                "risk_score": round(float(prob), 4),
                "top_features": [f.to_dict() for f in expl.top_features],
            }
        )

    results.sort(key=lambda x: x["risk_score"], reverse=True)
    return {"predictions": results, "horizon_minutes": 15}
