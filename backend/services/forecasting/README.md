# forecasting — Predictive Incident Forecasting

XGBoost-классификатор предсказывает вероятность того, что в ближайшие
**15 минут** по выбранному сервису начнётся инцидент. Работает поверх
данных, которые уже собирает pipeline (`log_signals_1m`, `slo_burn`,
`anomaly_events`) — никаких новых подсистем сбора.

## Файлы

| Файл | Назначение |
|---|---|
| [features.py](features.py) | Feature engineering — 32 признака (counts, lags, rolling stats, trends, SLO burn) |
| [trainer.py](trainer.py) | Offline-обучение + evaluation на labeled synthetic dataset |
| [predictor.py](predictor.py) | Runtime-обёртка над `xgboost.Booster` (lazy-load из JSON) |
| [explainer.py](explainer.py) | SHAP TreeExplainer — top-5 факторов для каждого предсказания |
| [models/forecaster.json](models/) | Сериализованная обученная модель (автосоздаётся trainer'ом) |
| [models/forecaster_metrics.json](models/) | Метрики качества на test-split |

## Как обучить модель

```bash
# 1. Сгенерировать training dataset (7 дней логов с 40 инцидентами)
python3 e2e-artifacts/generate_training_dataset.py

# 2. Обучить (stratified split по умолчанию)
docker exec backend-api-1 python -m backend.services.forecasting.trainer
```

После обучения:
- `forecaster.json` — модель, читается через `IncidentForecaster`;
- `forecaster_metrics.json` — отчёт по качеству (ROC-AUC, PR-AUC, F1,
  feature_importance), доступен также через `GET /forecasting/info`.

## Использование

```python
from backend.services.forecasting import (
    IncidentForecaster,
    build_feature_matrix,
    explain_prediction,
)

# Читаем signals/burn/anomaly_events из ClickHouse...
points = build_feature_matrix(signal_rows, burn_rows, anomaly_rows)

fc = IncidentForecaster()
probs = fc.predict_proba(points)          # np.ndarray ∈ [0, 1]
explanations = explain_prediction(fc, points, probs, top_n=5)
```

API-обёртка: [backend/api/forecasting.py](../../api/forecasting.py).

## Метрики (на synthetic dataset, 60 480 точек, 1 160 positive)

| Split | ROC-AUC | PR-AUC | F1 | Precision | Recall |
|---|---:|---:|---:|---:|---:|
| Stratified random (ML benchmark) | **0.978** | 0.785 | 0.717 | 0.770 | 0.671 |
| Time-based (production-realistic) | 0.769 | 0.538 | 0.621 | **0.967** | 0.458 |

Обоснование выбора XGBoost + детали feature engineering — в блоке R
документа [COURSEWORK_CONTRIBUTION.md](../../../COURSEWORK_CONTRIBUTION.md).
