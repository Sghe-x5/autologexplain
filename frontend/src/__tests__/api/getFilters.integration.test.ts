import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { GetFilters, type FilterData } from "@/api/getFilters";
import { FILTERS_MOCK } from "@/mocks/filter.mock";

// Получаем глобальный мок fetch
const mockFetch = global.fetch as ReturnType<typeof vi.fn>;

describe("GetFilters Integration Tests", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe("Сценарии успешной загрузки", () => {
    it("должен обрабатывать пустой массив фильтров", async () => {
      const emptyFilters: FilterData[] = [];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(emptyFilters),
      } as Response);

      const result = await GetFilters();

      expect(result).toEqual(emptyFilters);
      expect(result).toHaveLength(0);
    });

    it("должен обрабатывать фильтры с одним продуктом и одним сервисом", async () => {
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

    it("должен обрабатывать фильтры с множественными сервисами и окружениями", async () => {
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
      expect(result[0].services[1].environments).toHaveLength(2);
      expect(result[0].services[2].environments).toHaveLength(1);
    });
  });

  describe("Сценарии обработки ошибок", () => {
    it("должен обрабатывать ошибку сети и возвращать моковые данные", async () => {
      mockFetch.mockRejectedValueOnce(new Error("Network timeout"));

      const result = await GetFilters();

      expect(result).toEqual(FILTERS_MOCK);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("должен обрабатывать ошибку JSON парсинга и возвращать моковые данные", async () => {
      mockFetch.mockResolvedValueOnce({
        json: () => Promise.reject(new SyntaxError("Invalid JSON")),
      } as Response);

      const result = await GetFilters();

      expect(result).toEqual(FILTERS_MOCK);
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    it("должен обрабатывать ошибку с неожиданным типом данных", async () => {
      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(null),
      } as Response);

      await expect(GetFilters()).rejects.toThrow("Filters must be an array");
    });
  });

  describe("Сценарии валидации данных", () => {
    it("должен валидировать корректную структуру данных", async () => {
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
        {
          product: "valid-product-2",
          services: [
            {
              service: "valid-service-2",
              environments: ["staging", "qa"],
            },
          ],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(validData),
      } as Response);

      const result = await GetFilters();

      expect(result).toEqual(validData);
      expect(result).toHaveLength(2);

      // Проверяем структуру первого элемента
      expect(result[0]).toHaveProperty("product");
      expect(result[0]).toHaveProperty("services");
      expect(typeof result[0].product).toBe("string");
      expect(Array.isArray(result[0].services)).toBe(true);

      // Проверяем структуру сервисов
      expect(result[0].services[0]).toHaveProperty("service");
      expect(result[0].services[0]).toHaveProperty("environments");
      expect(typeof result[0].services[0].service).toBe("string");
      expect(Array.isArray(result[0].services[0].environments)).toBe(true);
    });

    it("должен выбрасывать ошибку при неполной структуре данных", async () => {
      const incompleteData = [
        {
          product: "incomplete-product",
          // отсутствует services
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(incompleteData),
      } as Response);

      await expect(GetFilters()).rejects.toThrow(
        "Invalid 'services' at index 0"
      );
    });

    it("должен выбрасывать ошибку при неправильном типе product", async () => {
      const invalidData = [
        {
          product: 123, // должно быть строкой
          services: [
            {
              service: "test-service",
              environments: ["prod"],
            },
          ],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(invalidData),
      } as Response);

      await expect(GetFilters()).rejects.toThrow(
        "Invalid 'product' at index 0"
      );
    });

    it("должен выбрасывать ошибку при неправильном типе service", async () => {
      const invalidData = [
        {
          product: "test-product",
          services: [
            {
              service: ["not-a-string"], // должно быть строкой
              environments: ["prod"],
            },
          ],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(invalidData),
      } as Response);

      await expect(GetFilters()).rejects.toThrow("Invalid 'service' at [0][0]");
    });

    it("должен выбрасывать ошибку при неправильном типе environments", async () => {
      const invalidData = [
        {
          product: "test-product",
          services: [
            {
              service: "test-service",
              environments: [123, "prod", true], // содержит не строки
            },
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

  describe("Сценарии производительности", () => {
    it("должен быстро обрабатывать большие объемы данных", async () => {
      const largeData: FilterData[] = Array.from({ length: 100 }, (_, i) => ({
        product: `product-${i}`,
        services: Array.from({ length: 10 }, (_, j) => ({
          service: `service-${i}-${j}`,
          environments: ["prod", "staging", "dev", "qa"],
        })),
      }));

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(largeData),
      } as Response);

      const startTime = performance.now();
      const result = await GetFilters();
      const endTime = performance.now();

      expect(result).toEqual(largeData);
      expect(result).toHaveLength(100);
      expect(result[0].services).toHaveLength(10);

      // Проверяем что обработка заняла менее 100мс
      expect(endTime - startTime).toBeLessThan(100);
    });
  });

  describe("Сценарии граничных случаев", () => {
    it("должен обрабатывать фильтры с пустыми массивами services", async () => {
      const edgeCaseData: FilterData[] = [
        {
          product: "edge-product",
          services: [],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(edgeCaseData),
      } as Response);

      const result = await GetFilters();

      expect(result).toEqual(edgeCaseData);
      expect(result[0].services).toHaveLength(0);
    });

    it("должен обрабатывать фильтры с пустыми массивами environments", async () => {
      const edgeCaseData: FilterData[] = [
        {
          product: "edge-product",
          services: [
            {
              service: "edge-service",
              environments: [],
            },
          ],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(edgeCaseData),
      } as Response);

      const result = await GetFilters();

      expect(result).toEqual(edgeCaseData);
      expect(result[0].services[0].environments).toHaveLength(0);
    });

    it("должен обрабатывать фильтры с очень длинными строками", async () => {
      const longString = "a".repeat(1000);
      const edgeCaseData: FilterData[] = [
        {
          product: longString,
          services: [
            {
              service: longString,
              environments: [longString, longString],
            },
          ],
        },
      ];

      mockFetch.mockResolvedValueOnce({
        json: () => Promise.resolve(edgeCaseData),
      } as Response);

      const result = await GetFilters();

      expect(result).toEqual(edgeCaseData);
      expect(result[0].product).toBe(longString);
      expect(result[0].services[0].service).toBe(longString);
      expect(result[0].services[0].environments).toEqual([
        longString,
        longString,
      ]);
    });
  });
});
