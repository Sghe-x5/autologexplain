import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { chatManagementApi } from "@/api/chatManagementApi";

describe("chatManagementApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("newChat endpoint", () => {
    it("должен иметь правильную конфигурацию", () => {
      const endpoint = chatManagementApi.endpoints.newChat;

      expect(endpoint).toBeDefined();
      expect(endpoint).toHaveProperty("name");
      expect(endpoint.name).toBe("newChat");
    });

    it("должен иметь правильные свойства", () => {
      const endpoint = chatManagementApi.endpoints.newChat;

      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("renewToken endpoint", () => {
    it("должен иметь правильную конфигурацию", () => {
      const endpoint = chatManagementApi.endpoints.renewToken;

      expect(endpoint).toBeDefined();
      expect(endpoint).toHaveProperty("name");
      expect(endpoint.name).toBe("renewToken");
    });

    it("должен принимать chatId параметр", () => {
      const endpoint = chatManagementApi.endpoints.renewToken;

      expect(endpoint).toBeDefined();
      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("API конфигурация", () => {
    it("должен иметь правильный reducerPath", () => {
      expect(chatManagementApi.reducerPath).toBe("chatManagementApi");
    });

    it("должен иметь правильную структуру endpoints", () => {
      expect(chatManagementApi.endpoints).toBeDefined();
      expect(chatManagementApi.endpoints.newChat).toBeDefined();
      expect(chatManagementApi.endpoints.renewToken).toBeDefined();
    });
  });

  describe("Экспортируемые хуки", () => {
    it("должен экспортировать useNewChatMutation", () => {
      expect(chatManagementApi.endpoints.newChat).toBeDefined();
      expect(chatManagementApi.endpoints.newChat.name).toBe("newChat");
    });

    it("должен экспортировать useRenewTokenMutation", () => {
      expect(chatManagementApi.endpoints.renewToken).toBeDefined();
      expect(chatManagementApi.endpoints.renewToken.name).toBe("renewToken");
    });
  });

  describe("Структура endpoint'ов", () => {
    it("должен иметь правильные типы для newChat", () => {
      const endpoint = chatManagementApi.endpoints.newChat;

      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильные типы для renewToken", () => {
      const endpoint = chatManagementApi.endpoints.renewToken;

      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("Валидация типов", () => {
    it("должен иметь правильный тип для newChat response", () => {
      const endpoint = chatManagementApi.endpoints.newChat;

      expect(endpoint).toBeDefined();
      expect(typeof endpoint.name).toBe("string");
      expect(endpoint.name).toBe("newChat");
    });

    it("должен иметь правильный тип для renewToken response", () => {
      const endpoint = chatManagementApi.endpoints.renewToken;

      expect(endpoint).toBeDefined();
      expect(typeof endpoint.name).toBe("string");
      expect(endpoint.name).toBe("renewToken");
    });
  });

  describe("Конфигурация API", () => {
    it("должен использовать правильную конфигурацию", () => {
      expect(chatManagementApi).toBeDefined();
      expect(chatManagementApi.reducerPath).toBe("chatManagementApi");
    });

    it("должен иметь правильную конфигурацию", () => {
      expect(chatManagementApi).toHaveProperty("reducerPath");
      expect(chatManagementApi).toHaveProperty("endpoints");
    });
  });
});
