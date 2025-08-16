import { vi } from "vitest";

// Мокаем глобальные объекты для тестов
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: vi.fn().mockImplementation((query) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(), // deprecated
    removeListener: vi.fn(), // deprecated
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Мокаем ResizeObserver если он не доступен
global.ResizeObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Мокаем IntersectionObserver если он не доступен
global.IntersectionObserver = vi.fn().mockImplementation(() => ({
  observe: vi.fn(),
  unobserve: vi.fn(),
  disconnect: vi.fn(),
}));

// Мокаем fetch глобально
global.fetch = vi.fn();

// Мокаем console методы для чистых тестов
global.console = {
  ...console,
  // Отключаем логи в тестах, если нужно
  // log: vi.fn(),
  // warn: vi.fn(),
  // error: vi.fn(),
};
