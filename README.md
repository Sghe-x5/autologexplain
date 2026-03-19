# AutoLogExplain

Система интеллектуального мониторинга логов с автоматическим обнаружением аномалий, управлением инцидентами и анализом первопричин (Root Cause Analysis).

## Архитектура

```
FastAPI  ←→  ClickHouse
   ↕               ↕
Celery Beat  →  Workers (detector · correlator · rca)
   ↕
Redis (watermarks · distributed locks · incident cache)
```

**Стек:** Python 3.11 · FastAPI · Celery · ClickHouse · Redis · YandexGPT

---

## Что умеет система

### Оригинальная часть
- Приём и хранение логов в ClickHouse
- Объяснение логов через LLM (YandexGPT)
- WebSocket-чат по логам
- Категоризация и тегирование логов (`/logs/list`, `/logs/categories`)

### Добавленный интеллектуальный контур

#### 1. Сигнализация (1-минутные бакеты)
Каждую минуту Celery-воркер агрегирует логи в сигналы по ключу `service + environment + category + severity`. Результат пишется в таблицу `log_signals_1m`. Используется Redis watermark для инкрементальной обработки — не читаем уже обработанные строки.

#### 2. Обнаружение аномалий (MAD z-score)
По каждому сигналу считается базовая линия из исторических данных (настраиваемое окно, по умолчанию 3 часа). Аномалия детектируется по **Median Absolute Deviation** — устойчивому к выбросам аналогу z-score:

```
z = |x - median(baseline)| / (1.4826 * MAD(baseline))
```

Порог: `z > 3.5`. Два типа аномалий:
- `volume_spike` — резкий рост числа логов данного типа
- `new_fingerprint_burst` — появление новых паттернов сообщений, которых не было в baseline

#### 3. Log Fingerprinting (Drain + SHA1)
Сырые сообщения нормализуются: UUID, IP-адреса, числа с единицами (`42ms`, `30s`) заменяются на `<uuid>`, `<ip>`, `<num>`. Из нормализованного шаблона считается SHA1 — это fingerprint. 150 разных `payment X failed: timeout after 42ms` → один fingerprint.

#### 4. Корреляция инцидентов
Аномальные кандидаты группируются в инциденты по fingerprint + временному окну (настраиваемый merge window). Поддерживается полный lifecycle:

```
new → open → acknowledged → mitigated → resolved → reopened
```

Incidenы создаются автоматически без участия человека. Каждое событие (открытие, прикрепление кандидата, смена статуса, пересчёт RCA) записывается в `incident_events` — полная audit trail.

#### 5. Root Cause Analysis

**Автоматический (фоновый):** каждому инциденту присваивается `root_cause_score` по формуле:

```
score = 0.35 * anomaly + 0.25 * earliness + 0.20 * fanout + 0.20 * criticality
```

- `anomaly` — насколько сильно отклонение от нормы
- `earliness` — насколько рано относительно других сервисов началась аномалия
- `fanout` — как много других сервисов затронуто (граф зависимостей)
- `criticality` — вес сервиса в топологии

**On-demand (`POST /rca/analyze/{fingerprint}`):** полный отчёт с временной шкалой аномалий, cascade path, evidence templates и текстовым summary. Опционально — через YandexGPT.

#### 6. SLO Burn Rate
По каждому сервису считается скользящий error budget burn rate в окнах 5m / 1h / 6h. При `burn_rate_1h > 1.0` error budget сгорает быстрее, чем пополняется.

#### 7. Граф зависимостей (из трейсов)
Система автоматически строит топологию сервисов из `trace_id` — без ручной конфигурации. Ребро между двумя сервисами появляется, если они встречаются в одном трейсе. Используется в RCA для расчёта `fanout` и `criticality`.

---

## API

### Инциденты

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/incidents` | Список инцидентов с фильтрами (`status`, `service`, `environment`, `category`, `severity`, `q`) |
| `GET` | `/incidents/{id}` | Карточка инцидента |
| `POST` | `/incidents` | Ручное создание |
| `PATCH` | `/incidents/{id}/status` | Смена статуса |
| `GET` | `/incidents/{id}/timeline` | Audit trail событий |
| `GET` | `/incidents/{id}/evidence` | Evidence (сигналы, кандидаты, трейсы) |

### RCA

| Метод | Путь | Описание |
|---|---|---|
| `POST` | `/rca/analyze/{fingerprint}` | Полный RCA-отчёт по fingerprint |
| `GET` | `/rca/graph` | Граф зависимостей сервисов |
| `GET` | `/rca/templates` | Топ log-шаблонов (Drain-кластеризация) |

### Логи

| Метод | Путь | Описание |
|---|---|---|
| `GET` | `/logs/list` | Список логов с фильтрами и категоризацией |
| `GET` | `/logs/categories` | Группировка по категориям и severity |

---

## Таблицы ClickHouse

| Таблица | Назначение |
|---|---|
| `logs` | Исходные логи |
| `log_signals_1m` | 1-минутные агрегаты по `service+env+category+severity` |
| `log_fingerprints_catalog` | Каталог нормализованных шаблонов (SHA1 → template) |
| `anomaly_events` | Детектированные аномалии с z-score |
| `incident_candidates` | Кандидаты на инциденты (ReplacingMergeTree) |
| `incidents` | Инциденты с lifecycle (ReplacingMergeTree) |
| `incident_events` | Audit trail всех событий по инцидентам |
| `service_dependency_graph` | Рёбра графа зависимостей из трейсов |
| `slo_burn` | SLO burn rate по окнам 5m/1h/6h |

Все таблицы создаются автоматически при старте.

---

## Celery Workers

| Worker | Триггер | Задача |
|---|---|---|
| `run_signals_cycle` | каждые 60 сек | Агрегация логов в сигналы + fingerprinting |
| `run_anomaly_cycle` | каждые 60 сек | MAD z-score по сигналам → кандидаты |
| `run_correlator_cycle` | каждые 60 сек | Корреляция кандидатов → инциденты |
| `run_rca_cycle` | каждые 5 мин | Пересчёт RCA scores по открытым инцидентам |
| `run_slo_cycle` | каждые 5 мин | Обновление SLO burn rate |

Все воркеры используют distributed lock через Redis — безопасно при запуске нескольких инстанций.

---

## Запуск

```bash
cp backend/.env.example backend/.env
# Заполнить YANDEX_GPT_API_KEY, YANDEX_FOLDER_ID

docker compose -f backend/docker-compose.yaml up -d
```

API доступен на `http://localhost:8080`.

---

## Конфигурация (.env)

| Переменная | Описание |
|---|---|
| `CLICKHOUSE_HOST` | Хост ClickHouse |
| `REDIS_URL` | URL Redis |
| `YANDEX_GPT_API_KEY` | API ключ YandexGPT |
| `YANDEX_FOLDER_ID` | Folder ID Yandex Cloud |
| `SIGNALS_LOOKBACK_MINUTES` | Окно для сигналов (default: 60) |
| `ANOMALY_BASELINE_HOURS` | Baseline для MAD (default: 3) |
| `ANOMALY_THRESHOLD_Z` | Порог z-score (default: 3.5) |
| `INCIDENT_MERGE_WINDOW_MINUTES` | Окно слияния кандидатов (default: 30) |
| `INCIDENT_REOPEN_WINDOW_MINUTES` | Окно для reopened (default: 60) |
