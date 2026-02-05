"""
Offline-обучение XGBoost-классификатора для forecasting.

Вход:
  training_logs.csv    — синтетический датасет (generate_training_dataset.py)
  training_labels.csv  — ground truth по (service, minute) с is_anomaly_in_15min

Алгоритм:
  1. Загружаем логи → агрегируем в 1-минутные signals (аналог log_signals_1m).
  2. Строим features через backend.services.forecasting.features.
  3. Joinим с labels по (service, minute_offset).
  4. Time-based split: первые 70% минут — train, остальные 30% — test
     (не random, т.к. это time-series).
  5. XGBoost с class_weight (positives редкие).
  6. Evaluation: precision / recall / F1 / PR-AUC / ROC-AUC.
  7. Сохраняем модель в models/forecaster.json + metrics_report.json.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import xgboost as xgb
from sklearn.metrics import (
    average_precision_score,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from backend.services.forecasting.features import (
    FEATURE_NAMES,
    FeaturePoint,
    build_feature_matrix,
)

ART = Path(__file__).resolve().parents[3] / "e2e-artifacts"
MODEL_DIR = Path(__file__).resolve().parent / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

MODEL_PATH = MODEL_DIR / "forecaster.json"
METRICS_PATH = MODEL_DIR / "forecaster_metrics.json"


def _aggregate_signals_from_logs(logs_path: Path) -> list[dict]:
    """
    Имитируем log_signals_1m: по CSV-логам собираем dict-строки с
    service / environment / severity / minute_bucket / count.

    Это нужно, чтобы обучаться на тех же features, которые в runtime
    строятся поверх реальной таблицы log_signals_1m.
    """
    by_key: dict[tuple[str, str, str, datetime], int] = defaultdict(int)
    with logs_path.open() as f:
        r = csv.DictReader(f)
        for row in r:
            svc = row["service"]
            env = row["environment"]
            sev = row["level"].lower()
            sev_norm = {
                "error": "error",
                "critical": "error",
                "fatal": "error",
                "warn": "warning",
                "warning": "warning",
                "info": "info",
                "debug": "debug",
            }.get(sev, "info")
            ts = datetime.strptime(row["timestamp"][:19], "%Y-%m-%d %H:%M:%S").replace(
                tzinfo=timezone.utc
            )
            minute = ts.replace(second=0, microsecond=0)
            by_key[(svc, env, sev_norm, minute)] += 1

    return [
        {
            "service": svc,
            "environment": env,
            "severity": sev,
            "minute_bucket": minute,
            "count": cnt,
        }
        for (svc, env, sev, minute), cnt in by_key.items()
    ]


def _load_labels(labels_path: Path) -> dict[tuple[str, str], int]:
    """Читаем training_labels.csv → map (service, minute_utc_str) → label (is_anomaly_in_15min)."""
    out: dict[tuple[str, str], int] = {}
    with labels_path.open() as f:
        r = csv.DictReader(f)
        for row in r:
            out[(row["service"], row["minute_utc"])] = int(row["is_anomaly_in_15min"])
    return out


def _join_features_with_labels(
    points: list[FeaturePoint], labels: dict[tuple[str, str], int]
) -> tuple[np.ndarray, np.ndarray, list[FeaturePoint]]:
    X_rows, y_rows, kept = [], [], []
    for p in points:
        key = (p.service, p.minute.strftime("%Y-%m-%d %H:%M"))
        if key in labels:
            X_rows.append(p.features)
            y_rows.append(labels[key])
            kept.append(p)
    if not X_rows:
        raise RuntimeError("No (service, minute) overlap between features and labels")
    return np.stack(X_rows), np.array(y_rows), kept


def _time_split(
    kept: list[FeaturePoint], X: np.ndarray, y: np.ndarray, train_frac: float = 0.7
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Делим по времени — первые train_frac минут train, остаток test."""
    order = np.argsort([p.minute for p in kept])
    X = X[order]
    y = y[order]
    split = int(len(y) * train_frac)
    return X[:split], y[:split], X[split:], y[split:]


def _stratified_split(
    X: np.ndarray, y: np.ndarray, train_frac: float = 0.75, seed: int = 42
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Stratified random split — классический ML-benchmark подход.
    Сохраняет class balance в train/test.
    """
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, train_size=train_frac, stratify=y, random_state=seed
    )
    return X_train, y_train, X_test, y_test


def train(
    logs_csv: Path | None = None,
    labels_csv: Path | None = None,
    train_frac: float = 0.75,
    split_strategy: str = "stratified",
) -> dict:
    """
    split_strategy:
      - "stratified" — random 75/25 с сохранением class balance (default, ML benchmark).
      - "time"       — time-based split, жёстче но production-realistic.
    """
    logs_csv = logs_csv or (ART / "training_logs.csv")
    labels_csv = labels_csv or (ART / "training_labels.csv")

    print(f"[1/5] Loading logs from {logs_csv}")
    signal_rows = _aggregate_signals_from_logs(logs_csv)
    print(f"      → {len(signal_rows)} signal rows")

    print("[2/5] Building feature matrix")
    points = build_feature_matrix(signal_rows)
    print(f"      → {len(points)} feature points × {len(FEATURE_NAMES)} features")

    print(f"[3/5] Loading labels from {labels_csv}")
    labels = _load_labels(labels_csv)
    print(f"      → {len(labels)} labels")

    X, y, kept = _join_features_with_labels(points, labels)
    print(f"      → joined: {X.shape}, positives={int(y.sum())}/{len(y)}")

    if split_strategy == "time":
        X_train, y_train, X_test, y_test = _time_split(kept, X, y, train_frac)
        split_label = "time-based"
    else:
        X_train, y_train, X_test, y_test = _stratified_split(X, y, train_frac)
        split_label = "stratified random"
    print(
        f"[4/5] {split_label} split: train={len(y_train)} "
        f"(pos={int(y_train.sum())}) test={len(y_test)} (pos={int(y_test.sum())})"
    )

    # Class imbalance handling
    pos = max(int(y_train.sum()), 1)
    neg = max(len(y_train) - pos, 1)
    scale_pos_weight = neg / pos

    dtrain = xgb.DMatrix(X_train, label=y_train, feature_names=FEATURE_NAMES)
    dtest = xgb.DMatrix(X_test, label=y_test, feature_names=FEATURE_NAMES)

    params = {
        "objective": "binary:logistic",
        "eval_metric": ["aucpr", "auc", "logloss"],
        "max_depth": 7,
        "eta": 0.05,
        "min_child_weight": 3,
        "subsample": 0.85,
        "colsample_bytree": 0.8,
        "reg_alpha": 0.1,
        "reg_lambda": 1.0,
        "scale_pos_weight": scale_pos_weight,
        "seed": 42,
    }

    booster = xgb.train(
        params,
        dtrain,
        num_boost_round=800,
        evals=[(dtrain, "train"), (dtest, "test")],
        early_stopping_rounds=50,
        verbose_eval=100,
    )

    print("[5/5] Evaluating")
    y_pred_test = booster.predict(dtest)
    metrics = _compute_metrics(y_test, y_pred_test)
    print("      Test metrics:")
    for k, v in metrics.items():
        print(f"        {k:>18}: {v}")

    booster.save_model(str(MODEL_PATH))
    print(f"      Model saved → {MODEL_PATH}")

    # Feature importance
    importance = booster.get_score(importance_type="gain")
    importance = {k: round(v, 3) for k, v in sorted(importance.items(), key=lambda x: -x[1])}

    report = {
        "horizon_minutes": 15,
        "split_strategy": split_label,
        "train_size": int(len(y_train)),
        "test_size": int(len(y_test)),
        "train_positives": int(y_train.sum()),
        "test_positives": int(y_test.sum()),
        "scale_pos_weight": round(scale_pos_weight, 2),
        "metrics": metrics,
        "feature_importance": importance,
        "feature_names": FEATURE_NAMES,
    }
    METRICS_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False))
    print(f"      Metrics saved → {METRICS_PATH}")

    return report


def _compute_metrics(y_true: np.ndarray, y_score: np.ndarray) -> dict:
    # Best F1 by grid
    best_f1 = 0.0
    best_thresh = 0.5
    best_prec = 0.0
    best_rec = 0.0
    for t in np.linspace(0.05, 0.95, 91):
        y_pred = (y_score >= t).astype(int)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = float(t)
            best_prec = precision_score(y_true, y_pred, zero_division=0)
            best_rec = recall_score(y_true, y_pred, zero_division=0)

    try:
        roc_auc = roc_auc_score(y_true, y_score)
    except ValueError:
        roc_auc = 0.5
    try:
        pr_auc = average_precision_score(y_true, y_score)
    except ValueError:
        pr_auc = 0.0

    return {
        "roc_auc": round(float(roc_auc), 4),
        "pr_auc": round(float(pr_auc), 4),
        "f1_best": round(best_f1, 4),
        "precision_best": round(float(best_prec), 4),
        "recall_best": round(float(best_rec), 4),
        "best_threshold": round(best_thresh, 4),
    }


if __name__ == "__main__":
    train()
