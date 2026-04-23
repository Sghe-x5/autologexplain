# similar_incidents — retrieval похожих инцидентов

Находит top-k похожих инцидентов в истории по гибридному скорингу,
**без embeddings / sentence-transformers / vector DB**. Аргумент в пользу
такого подхода — прозрачность: каждая компонента score с документированным
весом, на защите легко объяснить что и почему.

## Формула

```
Score(A, B) =  0.25 · I[service_A == service_B]
             + 0.15 · I[category_A == category_B]
             + 0.10 · I[severity_A == severity_B]
             + 0.05 · I[environment_A == environment_B]
             + 0.15 · LCP(fingerprint_A, fingerprint_B) / 16    # longest common prefix
             + 0.20 · Jaccard(tokens(title_A), tokens(title_B))  # title similarity
             + 0.10 · (1 - |severity_ord(A) - severity_ord(B)| / 4)
```

Сумма весов = 1.0. Результат нормализован в [0, 1].

## Использование

```python
from backend.services.similar_incidents import top_k_similar

src_incident = get_incident("...")        # dict из incidents/repository
candidates = get_incidents(limit=500)      # все инциденты из истории
matches = top_k_similar(src_incident, candidates, k=5, min_score=0.1)

# matches = list[SimilarityMatch(incident_id, score, breakdown, incident)]
```

`breakdown` показывает **вклад каждого компонента** в итоговый score — это
ценно для UI: пользователь видит, по каким признакам инциденты похожи.

API-обёртка: `GET /incidents/{id}/similar?k=5`.

## Альтернатива (которую не выбрали) — sentence-transformers

Для курсовой проекта с малой историей инцидентов embedding-модель:
- даст иллюзию «семантики» на единицах примеров;
- требует GPU/значимого CPU для inference;
- непрозрачна — «почему эти инциденты похожи» объяснить труднее.

Гибридный score прозрачен и детерминирован.
