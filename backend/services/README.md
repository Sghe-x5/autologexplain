# backend/services

Сервисный слой бэкенда. Каждый модуль — независимая подсистема с чётко
обозначенной зоной ответственности; API-слой ([backend/api](../api)) и
Celery-таски ([backend/celery_worker.py](../celery_worker.py)) — тонкая
обвязка, пробрасывающая HTTP/WebSocket/расписание в эти сервисы.

## Карта модулей

### Семантический слой (обогащение сырых логов)

| Модуль | Роль |
|---|---|
| [log_tags.py](log_tags.py) | Rule-based категоризация (backend/frontend/database/network/…), нормализация severity, формирование origin/tags |
| [log_fingerprints.py](log_fingerprints.py) | Нормализация message template (UUID/IP/числа → placeholders) и SHA-1 fingerprint для группировки |
| [log_clustering.py](log_clustering.py) | Упрощённая реализация Drain-алгоритма для online-кластеризации шаблонов логов |

### Online-детектирование и инцидент-менеджмент (Celery cycles)

| Модуль | Роль |
|---|---|
| [signals/](signals/) | 1-минутная сигнализация по (service, env, category, severity, fingerprint) + MAD-детектор аномалий. Вход для incident-pipeline |
| [incidents/](incidents/) | 3-cycle pipeline: detector → correlator → RCA с persistence в ClickHouse (ReplacingMergeTree, versioned snapshots) и distributed lock на Redis |
| [anomaly_detector.py](anomaly_detector.py) | Standalone MAD z-score детектор (используется on-demand в `/rca/analyze`) |
| [incident_manager.py](incident_manager.py) | **Reference-реализация** scoring формулы (используется только в тестах, production-версия — в `incidents/engine.py`) |

### Root Cause Analysis и SLO

| Модуль | Роль |
|---|---|
| [rca_engine.py](rca_engine.py) | Оркестратор on-demand RCA: собирает evidence из anomaly_detector, dependency_graph, log_clustering, slo_tracker в структурированный `RcaReport` |
| [dependency_graph.py](dependency_graph.py) | Автопостроение графа зависимостей сервисов из `trace_id` логов + cascade-root detection |
| [slo_tracker.py](slo_tracker.py) | Multi-window burn rate (Google SRE Book) для каждого сервиса в окнах 1h/6h/24h с порогами 14.4×/6×/3× |

### ML-предсказание и explainability (Variant Y Lite)

| Модуль | Роль |
|---|---|
| [forecasting/](forecasting/) | XGBoost-классификатор «будет ли инцидент в ближайшие 15 минут» + SHAP explainability |
| [similar_incidents/](similar_incidents/) | Top-k похожих инцидентов по гибридному score (без embeddings / vector DB) |
| [postmortem/](postmortem/) | Template-based markdown-генератор постмортемов (без LLM) |

### Инфраструктурные helpers

| Модуль | Роль |
|---|---|
| [llm_service.py](llm_service.py) | Обёртка над YandexGPT |
| [tokens.py](tokens.py) | HMAC-SHA256 токены для чат-сессий WebSocket |
| [utils.py](utils.py) | `publish_ws_message` — публикация сообщений в Redis pub/sub канал чата |

## Ключевые инварианты

1. **Никакой бизнес-логики в API-слое.** `backend/api/*.py` только парсит HTTP,
   маршалит HTTPException и вызывает функции из `services/`.
2. **Celery-таски — тонкие обёртки.** [celery_worker.py](../celery_worker.py)
   только вызывает `run_*_cycle()` из сервисов под `distributed_lock`.
3. **Сервисы не знают про HTTP.** Сервис не импортирует FastAPI, не бросает
   HTTPException — только собственные `*Error`-классы, которые API-слой
   мапит в нужный статус-код.
4. **Лог-pipeline линейный**: logs → log_tags → log_fingerprints →
   signals → anomaly_events → incident_candidates → incidents → RCA.
   Каждый следующий слой читает output предыдущего.
5. **ML-модули opt-in**: если XGBoost-модель не обучена, `GET /forecasting/risk`
   возвращает 404 с инструкцией как её обучить. Это не ломает остальной pipeline.

## Тестирование

```bash
docker exec backend-api-1 python -m pytest backend/tests/unit/ -v
```

Каждый подмодуль сервиса имеет тесты в
[backend/tests/unit/services/](../tests/unit/services/).
