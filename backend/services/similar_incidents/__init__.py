"""
Similar Incidents Retrieval (Variant Y Lite).

Задача: по выбранному инциденту найти top-k похожих из истории. Поиск помогает
SRE-инженеру быстро найти прошлый похожий случай и reuse-нуть решение.

Стратегия (без embeddings / vector DB):
  - Гибридный скоринг: штрафы/бонусы за совпадения по ряду атрибутов инцидента,
    которые УЖЕ хранятся в таблице `incidents` (ReplacingMergeTree snapshots).
  - Каждому фактору (service, environment, category, severity, fingerprint-prefix,
    SLO alert, кол-во задетых сервисов) назначен вес.
  - Bag-of-tokens подобие по title (лёгкое нормализованное Jaccard).

Почему не embeddings: для курсовой проекта без реальной истории инцидентов
sentence-transformers даст иллюзию «семантического поиска» на трёх похожих
строках. Гибридный score — честно: смотрим на структурные признаки и титул.

Файл:
  scoring.py   — набор функций-скореров и API top_k_similar
"""

from backend.services.similar_incidents.scoring import (
    SimilarityMatch,
    top_k_similar,
)

__all__ = ["SimilarityMatch", "top_k_similar"]
