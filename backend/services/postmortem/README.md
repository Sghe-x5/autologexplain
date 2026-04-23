# postmortem — генератор markdown-постмортема

Собирает структурированный markdown-документ на основе данных, которые
система **уже хранит** про инцидент. Без LLM: template-based,
детерминированно, без hallucinations.

## Файлы

| Файл | Назначение |
|---|---|
| [generator.py](generator.py) | Генератор + структура `PostmortemInput` |

## Структура документа

Постмортем содержит 8 секций:

1. **Summary** — сервис, severity, root_cause, impact, burn rate.
2. **Timing** — open / acknowledged / mitigated / resolved / status.
3. **Root cause (автоматический RCA)** — сервис + score + breakdown
   факторов (anomaly × 0.35, earliness × 0.25, fanout × 0.2, criticality × 0.2).
4. **Evidence** — Drain-шаблоны (top-3) + candidate-сигналы с trace_ids.
5. **Timeline** — хронологический список событий из `incident_events`.
6. **Похожие инциденты** — таблица top-5 с similarity %.
7. **Action items** — чеклист-шаблон для ручного заполнения.
8. **Lessons learned** — placeholder.

## Использование

```python
from backend.services.postmortem import PostmortemInput, generate_postmortem

md = generate_postmortem(
    PostmortemInput(
        incident=incident_dict,
        timeline_events=timeline_events,
        evidence_candidates=candidate_events,
        similar_incidents=similar_matches,
        evidence_templates=drain_templates,
        author="sre-on-call",
    )
)

# Сохранить в файл / отправить в Slack / открыть в редакторе...
```

API: `GET /incidents/{id}/postmortem`.

## Почему не LLM

- LLM может **придумать** факты, которых нет в исходных данных (hallucination).
- На защите нельзя защитить: «почему модель такое написала».
- Template-based генератор **не может ошибиться в фактах** — он просто вставляет
  поля из structured data. Формулировки Lessons learned / Action items SRE
  дописывает вручную (это единственная часть, где нужен человек).
