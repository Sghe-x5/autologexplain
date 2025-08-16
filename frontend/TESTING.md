# Тестирование Frontend

Этот документ описывает как запускать и писать тесты для frontend части проекта.

## Установка зависимостей

```bash
npm install
```

## Запуск тестов

### Запуск всех тестов

```bash
npm test
```

### Запуск тестов в watch режиме

```bash
npm run test:watch
```

### Запуск тестов с UI интерфейсом

```bash
npm run test:ui
```

### Запуск тестов с покрытием

```bash
npm run test:coverage
```

## Структура тестов

### Основные тесты

- `src/__tests__/getFilters.test.ts` - Базовые тесты для функции GetFilters
- `src/__tests__/getFilters.integration.test.ts` - Интеграционные тесты для GetFilters
- `src/__tests__/api/chatManagementApi.test.ts` - Unit тесты для chatManagementApi
- `src/__tests__/api/chatManagementApi.integration.test.ts` - Интеграционные тесты для chatManagementApi

### Конфигурация

- `vitest.config.ts` - Конфигурация vitest
- `src/test-setup.ts` - Глобальные настройки для тестов

## Тестирование API функций

### Мокирование fetch

Все тесты используют мокированный `fetch` для имитации HTTP запросов:

```typescript
// Мокаем успешный ответ
mockFetch.mockResolvedValueOnce({
  json: () => Promise.resolve(mockData),
} as Response);

// Мокаем ошибку сети
mockFetch.mockRejectedValueOnce(new Error("Network error"));

// Мокаем HTTP ошибку
mockFetch.mockResolvedValueOnce({
  json: () => Promise.reject(new Error("Invalid JSON")),
} as Response);
```

### Примеры тестов

#### Тест успешного запроса

```typescript
it("должен успешно загружать фильтры с сервера", async () => {
  const mockResponse = [
    {
      product: "test-product",
      services: [
        {
          service: "test-service",
          environments: ["prod", "dev"],
        },
      ],
    },
  ];

  mockFetch.mockResolvedValueOnce({
    json: () => Promise.resolve(mockResponse),
  } as Response);

  const result = await GetFilters();

  expect(mockFetch).toHaveBeenCalledWith("http://46.21.246.90:8080/logs/tree", {
    method: "GET",
  });
  expect(result).toEqual(mockResponse);
});
```

#### Тест обработки ошибок

```typescript
it("должен возвращать моковые данные при ошибке сети", async () => {
  mockFetch.mockRejectedValueOnce(new Error("Network error"));

  const result = await GetFilters();

  expect(result).toEqual(FILTERS_MOCK);
});
```

#### Тест валидации данных

```typescript
it("должен выбрасывать ошибку при невалидных данных", async () => {
  const invalidData = { product: "invalid" };

  mockFetch.mockResolvedValueOnce({
    json: () => Promise.resolve(invalidData),
  } as Response);

  await expect(GetFilters()).rejects.toThrow("Filters must be an array");
});
```

#### Тест API endpoint

```typescript
it("должен успешно создавать новый чат", async () => {
  const mockResponse = {
    chat_id: "chat-123",
    token: "token-456",
  };

  mockFetch.mockResolvedValueOnce({
    ok: true,
    json: () => Promise.resolve(mockResponse),
  } as Response);

  const result = await chatManagementApi.endpoints.newChat.initiate().unwrap();

  expect(mockFetch).toHaveBeenCalledWith(`${baseUrl}/chats/new`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
  });
  expect(result).toEqual(mockResponse);
});
```

## Типы тестов

### 1. Unit тесты

Тестируют отдельные функции и компоненты в изоляции.

### 2. Integration тесты

Тестируют взаимодействие между различными частями системы.

### 3. Edge case тесты

Тестируют граничные случаи и неожиданные входные данные.

### 4. Performance тесты

Тестируют производительность функций с большими объемами данных.

## Лучшие практики

### 1. Именование тестов

Используйте описательные названия на русском языке:

```typescript
it("должен успешно загружать фильтры с сервера", async () => {
  // тест
});
```

### 2. Структура тестов

Группируйте связанные тесты в `describe` блоки:

```typescript
describe("GetFilters", () => {
  describe("Сценарии успешной загрузки", () => {
    // тесты успешных сценариев
  });

  describe("Сценарии обработки ошибок", () => {
    // тесты обработки ошибок
  });
});
```

### 3. Очистка моков

Всегда очищайте моки после каждого теста:

```typescript
beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});
```

### 4. Типизация

Используйте TypeScript типы для моков:

```typescript
const mockFetch = global.fetch as ReturnType<typeof vi.fn>;
```

## Отладка тестов

### Логирование

Для отладки можно временно включить логи:

```typescript
// В test-setup.ts раскомментируйте:
// log: vi.fn(),
// warn: vi.fn(),
// error: vi.fn(),
```

### Запуск конкретного теста

```bash
npm test -- --run getFilters.test.ts
```

### Запуск теста с конкретным названием

```bash
npm test -- --run -t "должен успешно загружать фильтры"
```

## Добавление новых тестов

1. Создайте файл `*.test.ts` в папке `src/__tests__/`
2. Импортируйте необходимые зависимости
3. Напишите тесты используя `describe`, `it`, `expect`
4. Добавьте моки для внешних зависимостей
5. Запустите тесты и убедитесь что они проходят

## Полезные команды vitest

- `vi.fn()` - создание мока функции
- `vi.clearAllMocks()` - очистка всех моков
- `vi.restoreAllMocks()` - восстановление оригинальных функций
- `vi.mock()` - мокирование модулей
- `vi.spyOn()` - создание spy для существующих функций
