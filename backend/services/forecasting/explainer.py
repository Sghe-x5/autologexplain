"""
SHAP-based объяснение forecasting-предсказаний.

Для каждой точки предсказания возвращаем:
  - base_value      — средний logit модели (до влияния фичей)
  - prediction      — итоговый risk ∈ [0, 1]
  - top_features    — список top-N фичей, которые СИЛЬНЕЕ ВСЕГО толкнули
                      предсказание (по |SHAP value|)

SHAP-values для tree-based моделей вычисляются точно (TreeExplainer),
без сэмплирования — поэтому дешево.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

import numpy as np

from backend.services.forecasting.features import FEATURE_NAMES, FeaturePoint


@dataclass
class FeatureContribution:
    name: str
    value: float
    shap: float  # log-odds contribution
    direction: str  # "up" / "down"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "value": round(self.value, 4),
            "shap": round(self.shap, 4),
            "direction": self.direction,
        }


@dataclass
class Explanation:
    service: str
    environment: str
    minute: str  # ISO
    prediction: float
    base_value: float
    top_features: list[FeatureContribution]

    def to_dict(self) -> dict:
        return {
            "service": self.service,
            "environment": self.environment,
            "minute": self.minute,
            "prediction": round(self.prediction, 4),
            "base_value": round(self.base_value, 4),
            "top_features": [f.to_dict() for f in self.top_features],
        }


def explain_prediction(
    forecaster,
    points: Sequence[FeaturePoint],
    predictions: np.ndarray,
    top_n: int = 5,
) -> list[Explanation]:
    """
    Returns per-point explanations.
    """
    if not points:
        return []

    import shap

    booster = forecaster.get_booster()
    X = np.stack([p.features for p in points], axis=0)

    explainer = shap.TreeExplainer(booster)
    shap_values = explainer.shap_values(X)
    base_value = float(explainer.expected_value) if np.isscalar(explainer.expected_value) else float(explainer.expected_value[0])

    out: list[Explanation] = []
    for i, point in enumerate(points):
        row = shap_values[i]
        # Ranking by absolute contribution
        ranked = sorted(
            zip(FEATURE_NAMES, point.features.tolist(), row.tolist(), strict=True),
            key=lambda x: abs(x[2]),
            reverse=True,
        )[:top_n]
        top = [
            FeatureContribution(
                name=name,
                value=float(val),
                shap=float(shap_v),
                direction="up" if shap_v > 0 else "down",
            )
            for name, val, shap_v in ranked
        ]
        out.append(
            Explanation(
                service=point.service,
                environment=point.environment,
                minute=point.minute.isoformat(timespec="seconds"),
                prediction=float(predictions[i]),
                base_value=base_value,
                top_features=top,
            )
        )
    return out
