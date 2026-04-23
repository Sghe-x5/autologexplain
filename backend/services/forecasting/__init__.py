"""
Predictive Incident Forecasting (Variant Y Lite).

Модуль добавляет раннее предупреждение инцидентов: бинарный классификатор
предсказывает вероятность того, что в ближайшие 15 минут по данному сервису
начнётся инцидент.

В отличие от реактивного контура (signals/anomaly_detector срабатывает ПОСЛЕ
начала аномалии), forecasting позволяет реагировать до фактического burst'а.

Принципы реализации:
  - Используем ТОЛЬКО признаки из уже работающего pipeline
    (log_signals_1m, slo_burn, anomaly_events) — не добавляем новых
    подсистем сбора данных.
  - Один табличный классификатор — XGBoost (gradient boosting). Ни LSTM,
    ни Prophet — они не оправданы на наших объёмах и добавляют сложность
    без выигрыша.
  - Интерпретируемость — через SHAP. Для каждого prediction возвращаем
    top-5 features, которые толкнули score вверх/вниз.

Компоненты:
  features.py   — извлечение признаков из log_signals_1m / slo_burn
  trainer.py    — offline-обучение + evaluation
  predictor.py  — runtime inference
  explainer.py  — SHAP explainability
"""

from backend.services.forecasting.features import FEATURE_NAMES, build_feature_matrix
from backend.services.forecasting.predictor import IncidentForecaster
from backend.services.forecasting.explainer import explain_prediction

__all__ = [
    "FEATURE_NAMES",
    "build_feature_matrix",
    "IncidentForecaster",
    "explain_prediction",
]
