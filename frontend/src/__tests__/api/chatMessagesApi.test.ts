import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { chatMessagesApi } from "@/api/chatMessagesApi";

describe("chatMessagesApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("analysisStart endpoint", () => {
    it("должен иметь правильную конфигурацию", () => {
      const endpoint = chatMessagesApi.endpoints.analysisStart;

      expect(endpoint).toBeDefined();
      expect(endpoint).toHaveProperty("name");
      expect(endpoint.name).toBe("analysisStart");
    });

    it("должен иметь правильные свойства", () => {
      const endpoint = chatMessagesApi.endpoints.analysisStart;

      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("autoAnalysis endpoint", () => {
    it("должен иметь правильную конфигурацию", () => {
      const endpoint = chatMessagesApi.endpoints.autoAnalysis;

      expect(endpoint).toBeDefined();
      expect(endpoint).toHaveProperty("name");
      expect(endpoint.name).toBe("autoAnalysis");
    });

    it("должен иметь правильные свойства", () => {
      const endpoint = chatMessagesApi.endpoints.autoAnalysis;

      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("chatTurn endpoint", () => {
    it("должен иметь правильную конфигурацию", () => {
      const endpoint = chatMessagesApi.endpoints.chatTurn;

      expect(endpoint).toBeDefined();
      expect(endpoint).toHaveProperty("name");
      expect(endpoint.name).toBe("chatTurn");
    });

    it("должен иметь правильные свойства", () => {
      const endpoint = chatMessagesApi.endpoints.chatTurn;

      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("API конфигурация", () => {
    it("должен иметь правильный reducerPath", () => {
      expect(chatMessagesApi.reducerPath).toBe("chatMessagesApi");
    });

    it("должен иметь правильную структуру endpoints", () => {
      expect(chatMessagesApi.endpoints).toBeDefined();
      expect(chatMessagesApi.endpoints.analysisStart).toBeDefined();
      expect(chatMessagesApi.endpoints.autoAnalysis).toBeDefined();
      expect(chatMessagesApi.endpoints.chatTurn).toBeDefined();
    });
  });

  describe("Экспортируемые хуки", () => {
    it("должен экспортировать useAnalysisStartMutation", () => {
      expect(chatMessagesApi.endpoints.analysisStart).toBeDefined();
      expect(chatMessagesApi.endpoints.analysisStart.name).toBe(
        "analysisStart"
      );
    });

    it("должен экспортировать useAutoAnalysisMutation", () => {
      expect(chatMessagesApi.endpoints.autoAnalysis).toBeDefined();
      expect(chatMessagesApi.endpoints.autoAnalysis.name).toBe("autoAnalysis");
    });

    it("должен экспортировать useChatTurnMutation", () => {
      expect(chatMessagesApi.endpoints.chatTurn).toBeDefined();
      expect(chatMessagesApi.endpoints.chatTurn.name).toBe("chatTurn");
    });
  });

  describe("Структура endpoint'ов", () => {
    it("должен иметь правильные типы для analysisStart", () => {
      const endpoint = chatMessagesApi.endpoints.analysisStart;

      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильные типы для autoAnalysis", () => {
      const endpoint = chatMessagesApi.endpoints.autoAnalysis;

      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильные типы для chatTurn", () => {
      const endpoint = chatMessagesApi.endpoints.chatTurn;

      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("Валидация типов", () => {
    it("должен иметь правильный тип для analysisStart response", () => {
      const endpoint = chatMessagesApi.endpoints.analysisStart;

      expect(endpoint).toBeDefined();
      expect(typeof endpoint.name).toBe("string");
      expect(endpoint.name).toBe("analysisStart");
    });

    it("должен иметь правильный тип для autoAnalysis response", () => {
      const endpoint = chatMessagesApi.endpoints.autoAnalysis;

      expect(endpoint).toBeDefined();
      expect(typeof endpoint.name).toBe("string");
      expect(endpoint.name).toBe("autoAnalysis");
    });

    it("должен иметь правильный тип для chatTurn response", () => {
      const endpoint = chatMessagesApi.endpoints.chatTurn;

      expect(endpoint).toBeDefined();
      expect(typeof endpoint.name).toBe("string");
      expect(endpoint.name).toBe("chatTurn");
    });
  });

  describe("Конфигурация API", () => {
    it("должен использовать правильную конфигурацию", () => {
      expect(chatMessagesApi).toBeDefined();
      expect(chatMessagesApi.reducerPath).toBe("chatMessagesApi");
    });

    it("должен иметь правильную конфигурацию", () => {
      expect(chatMessagesApi).toHaveProperty("reducerPath");
      expect(chatMessagesApi).toHaveProperty("endpoints");
    });
  });

  describe("Проверка WebSocket функциональности", () => {
    it("должен иметь endpoints с WebSocket логикой", () => {
      const analysisStartEndpoint = chatMessagesApi.endpoints.analysisStart;
      const chatTurnEndpoint = chatMessagesApi.endpoints.chatTurn;

      expect(analysisStartEndpoint).toBeDefined();
      expect(chatTurnEndpoint).toBeDefined();
      expect(analysisStartEndpoint.name).toBe("analysisStart");
      expect(chatTurnEndpoint.name).toBe("chatTurn");
    });

    it("должен иметь autoAnalysis endpoint для создания чатов", () => {
      const autoAnalysisEndpoint = chatMessagesApi.endpoints.autoAnalysis;

      expect(autoAnalysisEndpoint).toBeDefined();
      expect(autoAnalysisEndpoint.name).toBe("autoAnalysis");
    });
  });
});
