"""
Automated postmortem generator (Variant Y Lite).

Собирает structured markdown-документ на основе данных, которые система
уже хранит про инцидент:
  - метаданные из incidents snapshot (service, category, severity, RCA-breakdown)
  - timeline из incident_events
  - evidence из incident candidates
  - похожие инциденты из similar_incidents
  - top-шаблоны из log_clustering (если переданы)

Без LLM. Шаблон честный: видно, что автоматически сгенерировано на основе
structured data. Пользователь может скопировать и доработать вручную.
"""

from backend.services.postmortem.generator import (
    PostmortemInput,
    generate_postmortem,
)

__all__ = ["PostmortemInput", "generate_postmortem"]
