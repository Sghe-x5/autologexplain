## Логи: категории и важность

Новые эндпоинты, чтобы сразу видеть источник и тип лога и быстро фильтровать/группировать записи.

### 1) Список логов

- `GET /logs/list`
- Параметры: `limit` (по умолчанию 200, максимум 1000), `product`, `service`, `environment`, `level`, `severity` (derived), `category`, `q` (поиск по сообщению, case-insensitive).
- Ответ: `items` — массив логов c полями `category`, `category_reason`, `severity`, `origin`, `tags`, `message`, `product`, `service`, `environment`, `level`, `status_code`, `trace_id`, `metadata`; `count` — число элементов в выдаче.

### 2) Группировка по категориям/уровням

- `GET /logs/categories`
- Те же фильтры (кроме `category`) + `limit` (по умолчанию 500).
- Ответ: `categories` (список `{category, count}`), `levels` (список `{severity, count}`), `total` — сколько записей анализировалось.

### Как рассчитывается категория/важность

- **Категории**: пытаемся взять `metadata.category`/`layer`/`component`; иначе применяем правила по ключевым словам в `service/product/environment/message`. Список: `backend`, `frontend`, `database`, `network`, `infrastructure`, `os_system`, `unknown`. Поле `category_reason` показывает, почему выбрана категория: `from_metadata:<key>`, `keyword:<match>`, `default:unknown`.
- **Severity**: нормализация `level` (`info/warning/error/critical/debug`); если уровня нет, используем `status_code` (`>=500` → critical, `>=400` → error, иначе info). Фильтровать можно через `?severity=error`.
- **Origin**: компактная строка `product/service@environment`.
- **Tags**: `[category, severity]` — удобно для фильтров на клиенте.

### Быстрые примеры

```bash
curl 'http://localhost:8080/logs/list?product=maps&limit=50'
curl 'http://localhost:8080/logs/list?category=database&q=timeout'
curl 'http://localhost:8080/logs/categories?service=postgres&limit=300'
```

## Incident Intelligence Engine (AutoRCA + SLO Guard)

Добавлен новый контур инцидентов:

- `detector-worker` (Celery beat): robust z-score (MAD) по `service+environment+category+severity`,
  пишет сигналы в `log_signals_1m`, аномалии в `incident_candidates`, SLO burn в `slo_burn`.
- `correlator-worker`: группирует кандидаты в инциденты (fingerprint + temporal merge), ведёт lifecycle
  `open -> acknowledged -> mitigated -> resolved -> reopened`.
- `rca-worker`: пересчитывает root-cause rank по формуле
  `0.35*anomaly + 0.25*earliness + 0.2*fanout + 0.2*criticality`.
- Redis: distributed lock для идемпотентности фоновых задач + cache карточек инцидентов.

### Новые таблицы ClickHouse

- `log_signals_1m`
- `incident_candidates`
- `incidents`
- `incident_events`
- `service_dependency_graph`
- `slo_burn`

Таблицы создаются автоматически при старте API/worker.

### Incident API

- `GET /incidents` — список c фильтрами (`status`, `service`, `environment`, `category`, `severity`, `q`).
- `GET /incidents/{incident_id}` — карточка инцидента.
- `POST /incidents` — ручное создание инцидента.
- `PATCH /incidents/{incident_id}/status` — смена статуса.
- `GET /incidents/{incident_id}/timeline` — события lifecycle/evidence.
- `GET /incidents/{incident_id}/evidence` — evidence (signal/candidate trace).
