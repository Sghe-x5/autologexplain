import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { GetFilters, type FilterData } from "@/api/getFilters";

// Глобальный мок fetch
const mockFetch = global.fetch as ReturnType<typeof vi.fn>;

describe("GetFilters Integration Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Сценарии успешной загрузки", () => {
    it("обрабатывает пустой массив фильтров", async () => {
      const emptyFilters: FilterData[] = [];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(emptyFilters),
      } as Response);

      const result = await GetFilters();

      expect(result).toEqual(emptyFilters);
      expect(result).toHaveLength(0);
    });

    it("обрабатывает один продукт и один сервис", async () => {
      const singleFilter: FilterData[] = [
        {
          product: "single-product",
          services: [
            {
              service: "single-service",
              environments: ["prod"],
            },
          ],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(singleFilter),
      } as Response);

      const result = await GetFilters();

      expect(result).toEqual(singleFilter);
      expect(result[0].services).toHaveLength(1);
      expect(result[0].services[0].environments).toHaveLength(1);
    });

    it("обрабатывает множественные сервисы и окружения", async () => {
      const complexFilters: FilterData[] = [
        {
          product: "multi-service-product",
          services: [
            {
              service: "service-1",
              environments: ["prod", "staging", "dev", "qa", "test"],
            },
            {
              service: "service-2",
              environments: ["prod", "staging"],
            },
            {
              service: "service-3",
              environments: ["prod"],
            },
          ],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(complexFilters),
      } as Response);

      const result = await GetFilters();

      expect(result).toEqual(complexFilters);
      expect(result[0].services).toHaveLength(3);
      expect(result[0].services[0].environments).toHaveLength(5);
    });
  });

  describe("Сценарии ошибок", () => {
    it("кидает при ошибке сети", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network timeout"));
      await expect(GetFilters()).rejects.toThrow();
    });

    it("кидает при ошибке JSON парсинга", async () => {
      mockFetch.mockResolvedValueOnce({
        json: () => Promise.reject(new SyntaxError("Invalid JSON")),
      } as Response);
      await expect(GetFilters()).rejects.toThrow();
    });

    it("кидает если сервер вернул неожиданный тип данных", async () => {
      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(null),
      } as Response);
      await expect(GetFilters()).rejects.toThrow("Filters must be an array");
    });
  });

  describe("Сценарии валидации", () => {
    it("валидирует корректную структуру данных", async () => {
      const validData: FilterData[] = [
        {
          product: "valid-product-1",
          services: [
            {
              service: "valid-service-1",
              environments: ["prod", "dev"],
            },
          ],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(validData),
      } as Response);

      const result = await GetFilters();
      expect(result).toEqual(validData);
    });

    it("кидает при отсутствии services", async () => {
      const incompleteData = [
        {
          product: "incomplete-product",
          // нет services
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(incompleteData),
      } as Response);

      await expect(GetFilters()).rejects.toThrow(
        "Invalid 'services' at index 0"
      );
    });

    it("кидает при неправильном типе product", async () => {
      const invalidData = [
        {
          product: 123,
          services: [{ service: "test-service", environments: ["prod"] }],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(invalidData),
      } as Response);

      await expect(GetFilters()).rejects.toThrow(
        "Invalid 'product' at index 0"
      );
    });

    it("кидает при неправильном типе service", async () => {
      const invalidData = [
        {
          product: "test-product",
          services: [{ service: ["not-a-string"], environments: ["prod"] }],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(invalidData),
      } as Response);

      await expect(GetFilters()).rejects.toThrow("Invalid 'service' at [0][0]");
    });

    it("кидает при неправильном типе environments", async () => {
      const invalidData = [
        {
          product: "test-product",
          services: [
            { service: "test-service", environments: [123, "prod", true] },
          ],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(invalidData),
      } as Response);

      await expect(GetFilters()).rejects.toThrow(
        "Invalid 'environments' at [0][0]"
      );
    });
  });

  describe("Граничные случаи", () => {
    it("обрабатывает фильтры с пустым services", async () => {
      const edgeCaseData: FilterData[] = [
        { product: "edge-product", services: [] },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(edgeCaseData),
      } as Response);

      const result = await GetFilters();
      expect(result).toEqual(edgeCaseData);
    });

    it("обрабатывает фильтры с пустыми environments", async () => {
      const edgeCaseData: FilterData[] = [
        {
          product: "edge-product",
          services: [{ service: "s", environments: [] }],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(edgeCaseData),
      } as Response);

      const result = await GetFilters();
      expect(result).toEqual(edgeCaseData);
    });

    it("обрабатывает очень длинные строки", async () => {
      const long = "a".repeat(1000);
      const edgeCaseData: FilterData[] = [
        {
          product: long,
          services: [{ service: long, environments: [long, long] }],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(edgeCaseData),
      } as Response);

      const result = await GetFilters();
      expect(result[0].product).toBe(long);
      expect(result[0].services[0].service).toBe(long);
      expect(result[0].services[0].environments).toEqual([long, long]);
    });
  });
});
