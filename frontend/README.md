# Frontend Application

Современное веб-приложение, построенное на React с использованием TypeScript, Vite и Tailwind CSS.

## Технологический стек

- **React 19** - современная библиотека для создания пользовательских интерфейсов
- **TypeScript** - типизированный JavaScript для повышения надежности кода
- **Vite** - быстрый инструмент сборки для современной веб-разработки
- **Tailwind CSS** - utility-first CSS фреймворк для быстрого создания интерфейсов
- **Redux Toolkit** - управление состоянием приложения
- **React Hook Form** - управление формами
- **Zod** - валидация схем данных
- **Radix UI** - доступные и настраиваемые компоненты интерфейса

## Структура проекта

```
src/
├── components/     # Переиспользуемые UI компоненты
├── features/       # Функциональные модули (DatePicker, TimePicker)
├── pages/         # Страницы приложения
├── widgets/       # Сложные виджеты (LogExplainModal)
├── api/           # API клиенты и схемы
├── lib/           # Утилиты и хелперы
├── consts/        # Константы приложения
└── mocks/         # Моки для тестирования
```

## Разработка

### Установка зависимостей

```bash
npm install
```

### Запуск в режиме разработки

```bash
npm run dev
```

Приложение будет доступно по адресу: http://localhost:5173

### Сборка проекта

```bash
npm run build
```

### Предварительный просмотр сборки

```bash
npm run preview
```

### Линтинг и тестирование

```bash
npm run lint      # Проверка кода ESLint
npm run test      # Запуск тестов Vitest
```

## Production развертывание

### Вариант 1: Docker (рекомендуется)

#### Сборка Docker образа

```bash
docker build -t frontend-app .
```

#### Запуск контейнера

```bash
docker run -d -p 5173:5173 --name frontend frontend-app
```

Приложение будет доступно по адресу: http://localhost:5173

#### Использование Docker Compose

Создайте `docker-compose.yml`:

```yaml
version: "3.8"
services:
  frontend:
    build: .
    ports:
      - "5173:5173"
    restart: unless-stopped
```

Запуск:

```bash
docker compose up -d
```

### Вариант 2: Ручное развертывание

#### 1. Сборка проекта

```bash
npm run build
```

#### 2. Установка веб-сервера

```bash
npm install -g serve
```

#### 3. Запуск веб-сервера

```bash
serve -s dist -l 5173
```
