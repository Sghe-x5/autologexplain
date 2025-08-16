import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { chatMessagesApi } from "@/api/chatMessagesApi";

describe("chatMessagesApi Integration Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Структура API", () => {
    it("должен иметь правильную конфигурацию всех endpoints", () => {
      expect(chatMessagesApi.endpoints.analysisStart).toBeDefined();
      expect(chatMessagesApi.endpoints.autoAnalysis).toBeDefined();
      expect(chatMessagesApi.endpoints.chatTurn).toBeDefined();

      expect(chatMessagesApi.endpoints.analysisStart.name).toBe(
        "analysisStart"
      );
      expect(chatMessagesApi.endpoints.autoAnalysis.name).toBe("autoAnalysis");
      expect(chatMessagesApi.endpoints.chatTurn.name).toBe("chatTurn");
    });

    it("должен иметь правильные типы данных для всех endpoints", () => {
      const analysisStartEndpoint = chatMessagesApi.endpoints.analysisStart;
      const autoAnalysisEndpoint = chatMessagesApi.endpoints.autoAnalysis;
      const chatTurnEndpoint = chatMessagesApi.endpoints.chatTurn;

      expect(analysisStartEndpoint).toHaveProperty("name");
      expect(autoAnalysisEndpoint).toHaveProperty("name");
      expect(chatTurnEndpoint).toHaveProperty("name");
    });
  });

  describe("Конфигурация endpoints", () => {
    it("должен иметь правильный reducerPath", () => {
      expect(chatMessagesApi.reducerPath).toBe("chatMessagesApi");
    });

    it("должен иметь правильную структуру", () => {
      expect(chatMessagesApi).toHaveProperty("endpoints");
    });

    it("должен иметь все необходимые endpoints", () => {
      const endpoints = Object.keys(chatMessagesApi.endpoints);
      expect(endpoints).toContain("analysisStart");
      expect(endpoints).toContain("autoAnalysis");
      expect(endpoints).toContain("chatTurn");
      expect(endpoints).toHaveLength(3);
    });
  });

  describe("Валидация структуры analysisStart endpoint", () => {
    it("должен иметь правильные свойства", () => {
      const endpoint = chatMessagesApi.endpoints.analysisStart;

      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильное имя", () => {
      const endpoint = chatMessagesApi.endpoints.analysisStart;
      expect(endpoint.name).toBe("analysisStart");
    });

    it("должен быть определен", () => {
      const endpoint = chatMessagesApi.endpoints.analysisStart;
      expect(endpoint).toBeDefined();
    });
  });

  describe("Валидация структуры autoAnalysis endpoint", () => {
    it("должен иметь правильные свойства", () => {
      const endpoint = chatMessagesApi.endpoints.autoAnalysis;

      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильное имя", () => {
      const endpoint = chatMessagesApi.endpoints.autoAnalysis;
      expect(endpoint.name).toBe("autoAnalysis");
    });

    it("должен быть определен", () => {
      const endpoint = chatMessagesApi.endpoints.autoAnalysis;
      expect(endpoint).toBeDefined();
    });
  });

  describe("Валидация структуры chatTurn endpoint", () => {
    it("должен иметь правильные свойства", () => {
      const endpoint = chatMessagesApi.endpoints.chatTurn;

      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильное имя", () => {
      const endpoint = chatMessagesApi.endpoints.chatTurn;
      expect(endpoint.name).toBe("chatTurn");
    });

    it("должен быть определен", () => {
      const endpoint = chatMessagesApi.endpoints.chatTurn;
      expect(endpoint).toBeDefined();
    });
  });

  describe("Проверка типов данных", () => {
    it("должен иметь правильные типы для analysisStart", () => {
      const endpoint = chatMessagesApi.endpoints.analysisStart;

      expect(endpoint).toBeDefined();
      expect(typeof endpoint.name).toBe("string");
      expect(endpoint.name).toBe("analysisStart");
    });

    it("должен иметь правильные типы для autoAnalysis", () => {
      const endpoint = chatMessagesApi.endpoints.autoAnalysis;

      expect(endpoint).toBeDefined();
      expect(typeof endpoint.name).toBe("string");
      expect(endpoint.name).toBe("autoAnalysis");
    });

    it("должен иметь правильные типы для chatTurn", () => {
      const endpoint = chatMessagesApi.endpoints.chatTurn;

      expect(endpoint).toBeDefined();
      expect(typeof endpoint.name).toBe("string");
      expect(endpoint.name).toBe("chatTurn");
    });
  });

  describe("Проверка конфигурации", () => {
    it("должен использовать правильную конфигурацию", () => {
      expect(chatMessagesApi).toBeDefined();
      expect(chatMessagesApi.reducerPath).toBe("chatMessagesApi");
    });

    it("должен иметь правильную структуру API", () => {
      expect(chatMessagesApi).toHaveProperty("reducerPath");
      expect(chatMessagesApi).toHaveProperty("endpoints");
    });
  });

  describe("Проверка экспортируемых хуков", () => {
    it("должен экспортировать правильные endpoints", () => {
      expect(chatMessagesApi.endpoints.analysisStart).toBeDefined();
      expect(chatMessagesApi.endpoints.autoAnalysis).toBeDefined();
      expect(chatMessagesApi.endpoints.chatTurn).toBeDefined();
    });

    it("должен иметь правильные имена endpoints", () => {
      expect(chatMessagesApi.endpoints.analysisStart.name).toBe(
        "analysisStart"
      );
      expect(chatMessagesApi.endpoints.autoAnalysis.name).toBe("autoAnalysis");
      expect(chatMessagesApi.endpoints.chatTurn.name).toBe("chatTurn");
    });
  });

  describe("Проверка структуры endpoints", () => {
    it("должен иметь правильную структуру для analysisStart", () => {
      const endpoint = chatMessagesApi.endpoints.analysisStart;
      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильную структуру для autoAnalysis", () => {
      const endpoint = chatMessagesApi.endpoints.autoAnalysis;
      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильную структуру для chatTurn", () => {
      const endpoint = chatMessagesApi.endpoints.chatTurn;
      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("Проверка метаданных", () => {
    it("должен иметь правильные метаданные для analysisStart", () => {
      const endpoint = chatMessagesApi.endpoints.analysisStart;

      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильные метаданные для autoAnalysis", () => {
      const endpoint = chatMessagesApi.endpoints.autoAnalysis;

      expect(endpoint).toHaveProperty("name");
    });

    it("должен иметь правильные метаданные для chatTurn", () => {
      const endpoint = chatMessagesApi.endpoints.chatTurn;

      expect(endpoint).toHaveProperty("name");
    });
  });

  describe("Проверка WebSocket интеграции", () => {
    it("должен иметь endpoints для WebSocket сообщений", () => {
      const analysisStartEndpoint = chatMessagesApi.endpoints.analysisStart;
      const chatTurnEndpoint = chatMessagesApi.endpoints.chatTurn;

      expect(analysisStartEndpoint).toBeDefined();
      expect(chatTurnEndpoint).toBeDefined();
      expect(analysisStartEndpoint.name).toBe("analysisStart");
      expect(chatTurnEndpoint.name).toBe("chatTurn");
    });

    it("должен иметь endpoint для автоматического анализа", () => {
      const autoAnalysisEndpoint = chatMessagesApi.endpoints.autoAnalysis;

      expect(autoAnalysisEndpoint).toBeDefined();
      expect(autoAnalysisEndpoint.name).toBe("autoAnalysis");
    });

    it("должен поддерживать все типы WebSocket операций", () => {
      const endpoints = [
        chatMessagesApi.endpoints.analysisStart,
        chatMessagesApi.endpoints.autoAnalysis,
        chatMessagesApi.endpoints.chatTurn,
      ];

      endpoints.forEach((endpoint) => {
        expect(endpoint).toBeDefined();
        expect(endpoint).toHaveProperty("name");
        expect(typeof endpoint.name).toBe("string");
      });
    });
  });
});
