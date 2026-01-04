# Автотесты для API и логов сервиса

Этот репозиторий содержит набор автотестов для проверки функциональности API и сервиса логов, включая эндпоинты чатов, логов и healthcheck. Тесты интегрируются с Allure для генерации наглядных отчетов.

## Структура проекта

├── tests/ # Тесты для API, логов и WebSocket (мок)
│ ├── test_chats.py # Тесты для /chats/new и /chats/renew
│ ├── test_logs.py # Тесты для /logs/tree и /logs/health
├── utils/
│ └── api_client.py # HTTP клиент для тестов
├── requirements.txt # Все зависимости для запуска тестов
├── conftest.py # Фикстуры для тестов
├── .env.example # Пример настройки переменных окружения
└── README.md

## Установка зависимостей

Рекомендуется использовать виртуальное окружение Python:

```bash
python -m venv .venv
source .venv/bin/activate   # Linux/macOS
.venv\Scripts\activate      # Windows

pip install -r requirements.txt

```

## Настройка переменных окружения

Создайте .env в корне проекта с базовым URL вашего сервера:

```dotenv
API_BASE_URL=http://localhost:8080
```

## Запуск всех тестов

```bash
pytest --alluredir=allure-results
```

## Запуск конкретного файла:

```bash
pytest tests/test_chats.py --alluredir=allure-results
```

## Allure отчет

Сгенерировать отчет и открыть его:

```bash
allure serve allure-results
```
Либо сохранить в отдельную папку:

```bash
allure generate allure-results --clean -o allure-report
```



