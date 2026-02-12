"""
Runtime inference для forecasting-модели.

Класс IncidentForecaster:
  - загружает обученный XGBoost из файла (по умолчанию models/forecaster.json)
  - принимает список FeaturePoint → возвращает risk score ∈ [0, 1]
  - потокобезопасен (xgboost Booster singleton)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Sequence

import numpy as np

from backend.services.forecasting.features import FeaturePoint, FEATURE_NAMES

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent / "models" / "forecaster.json"


class IncidentForecaster:
    """Thin-wrapper над XGBoost Booster."""

    def __init__(self, model_path: str | os.PathLike | None = None) -> None:
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH
        self._booster = None  # lazy

    def loaded(self) -> bool:
        return self._booster is not None

    def _load(self):
        if self._booster is not None:
            return
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Forecaster model not found: {self.model_path}. "
                f"Run `python -m backend.services.forecasting.trainer` first."
            )
        import xgboost as xgb
        self._booster = xgb.Booster()
        self._booster.load_model(str(self.model_path))

    def predict_proba(self, points: Sequence[FeaturePoint]) -> np.ndarray:
        """
        Возвращает массив risk-scores ∈ [0, 1] для каждой точки.
        """
        if not points:
            return np.array([])
        self._load()
        import xgboost as xgb
        X = np.stack([p.features for p in points], axis=0)
        dmat = xgb.DMatrix(X, feature_names=FEATURE_NAMES)
        return self._booster.predict(dmat)

    def get_booster(self):
        """Для SHAP-explainer."""
        self._load()
        return self._booster

    @property
    def feature_names(self) -> list[str]:
        return list(FEATURE_NAMES)
