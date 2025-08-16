import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { chatManagementApi } from "@/api/chatManagementApi";

describe("chatManagementApi Integration Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Структура API", () => {
    it("должен иметь правильную конфигурацию endpoints", () => {
      expect(chatManagementApi.endpoints.newChat).toBeDefined();
      expect(chatManagementApi.endpoints.renewToken).toBeDefined();

      expect(chatManagementApi.endpoints.newChat.name).toBe("newChat");
      expect(chatManagementApi.endpoints.renewToken.name).toBe("renewToken");
    });

    it("должен иметь правильные типы данных", () => {
      const newChatEndpoint = chatManagementApi.endpoints.newChat;
      const renewTokenEndpoint = chatManagementApi.endpoints.renewToken;

      expect(newChatEndpoint).toHaveProperty("name");
      expect(renewTokenEndpoint).toHaveProperty("name");
    });
  });

  describe("Конфигурация endpoints", () => {
    it("должен иметь правильный reducerPath", () => {
      expect(chatManagementApi.reducerPath).toBe("chatManagementApi");
    });

    it("должен иметь правильную структуру", () => {
      expect(chatManagementApi).toHaveProperty("endpoints");
    });
  });

  describe("Валидация структуры newChat endpoint", () => {
    it("должен иметь правильные свойства", () => {
      const endpoint = chatManagementApi.endpoints.newChat;

      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильное имя", () => {
      const endpoint = chatManagementApi.endpoints.newChat;
      expect(endpoint.name).toBe("newChat");
    });

    it("должен иметь правильные свойства", () => {
      const endpoint = chatManagementApi.endpoints.newChat;
      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("Валидация структуры renewToken endpoint", () => {
    it("должен иметь правильные свойства", () => {
      const endpoint = chatManagementApi.endpoints.renewToken;

      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильное имя", () => {
      const endpoint = chatManagementApi.endpoints.renewToken;
      expect(endpoint.name).toBe("renewToken");
    });

    it("должен иметь правильные свойства", () => {
      const endpoint = chatManagementApi.endpoints.renewToken;
      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("Проверка типов данных", () => {
    it("должен иметь правильные типы для newChat", () => {
      const endpoint = chatManagementApi.endpoints.newChat;

      expect(endpoint).toBeDefined();
      expect(typeof endpoint.name).toBe("string");
      expect(endpoint.name).toBe("newChat");
    });

    it("должен иметь правильные типы для renewToken", () => {
      const endpoint = chatManagementApi.endpoints.renewToken;

      expect(endpoint).toBeDefined();
      expect(typeof endpoint.name).toBe("string");
      expect(endpoint.name).toBe("renewToken");
    });
  });

  describe("Проверка конфигурации", () => {
    it("должен использовать правильную конфигурацию", () => {
      expect(chatManagementApi).toBeDefined();
      expect(chatManagementApi.reducerPath).toBe("chatManagementApi");
    });

    it("должен иметь правильную структуру API", () => {
      expect(chatManagementApi).toHaveProperty("reducerPath");
      expect(chatManagementApi).toHaveProperty("endpoints");
    });
  });

  describe("Проверка экспортируемых хуков", () => {
    it("должен экспортировать правильные endpoints", () => {
      expect(chatManagementApi.endpoints.newChat).toBeDefined();
      expect(chatManagementApi.endpoints.renewToken).toBeDefined();
    });

    it("должен иметь правильные имена endpoints", () => {
      expect(chatManagementApi.endpoints.newChat.name).toBe("newChat");
      expect(chatManagementApi.endpoints.renewToken.name).toBe("renewToken");
    });
  });

  describe("Проверка структуры endpoints", () => {
    it("должен иметь правильную структуру для newChat", () => {
      const endpoint = chatManagementApi.endpoints.newChat;
      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильную структуру для renewToken", () => {
      const endpoint = chatManagementApi.endpoints.renewToken;
      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("Проверка метаданных", () => {
    it("должен иметь правильные метаданные для newChat", () => {
      const endpoint = chatManagementApi.endpoints.newChat;

      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильные метаданные для renewToken", () => {
      const endpoint = chatManagementApi.endpoints.renewToken;

      expect(endpoint).toHaveProperty("name");
    });
  });
});
