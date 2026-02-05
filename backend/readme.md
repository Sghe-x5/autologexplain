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
