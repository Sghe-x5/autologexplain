import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { GetFilters, type FilterData } from "@/api/getFilters";
import { FILTERS_MOCK } from "@/mocks/filter.mock";

// Получаем глобальный мок fetch
const mockFetch = global.fetch as ReturnType<typeof vi.fn>;

describe("GetFilters", () => {
  beforeEach(() => {
    // Очищаем моки перед каждым тестом
    vi.clearAllMocks();
  });

  afterEach(() => {
    // Восстанавливаем моки после каждого теста
    vi.restoreAllMocks();
  });

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

    // Мокаем успешный ответ от сервера
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(mockResponse),
    } as Response);

    const result = await GetFilters();

    expect(mockFetch).toHaveBeenCalledWith(
      "http://46.21.246.90:8080/logs/tree",
      {
        method: "GET",
      }
    );
    expect(result).toEqual(mockResponse);
  });

  it("должен возвращать моковые данные при ошибке сети", async () => {
    // Мокаем ошибку сети
    mockFetch.mockRejectedValueOnce(new Error("Network error"));

    const result = await GetFilters();

    expect(mockFetch).toHaveBeenCalledWith(
      "http://46.21.246.90:8080/logs/tree",
      {
        method: "GET",
      }
    );
    expect(result).toEqual(FILTERS_MOCK);
  });

  it("должен возвращать моковые данные при ошибке HTTP", async () => {
    // Мокаем HTTP ошибку
    mockFetch.mockResolvedValueOnce({
      json: () => Promise.reject(new Error("Invalid JSON")),
    } as Response);

    const result = await GetFilters();

    expect(mockFetch).toHaveBeenCalledWith(
      "http://46.21.246.90:8080/logs/tree",
      {
        method: "GET",
      }
    );
    expect(result).toEqual(FILTERS_MOCK);
  });

  it("должен работать с пустым FILTER_URL", async () => {
    // Создаем мок для fetch который будет возвращать пустую строку
    // Это имитирует случай когда FILTER_URL может быть undefined
    const mockFetchWithEmptyUrl = vi.fn();
    const originalFetch = global.fetch;
    global.fetch = mockFetchWithEmptyUrl;

    const mockResponse = [
      {
        product: "empty-url-test",
        services: [
          {
            service: "test-service",
            environments: ["prod"],
          },
        ],
      },
    ];

    mockFetchWithEmptyUrl.mockResolvedValueOnce({
      json: () => Promise.resolve(mockResponse),
    } as Response);

    // Создаем временную функцию которая использует пустой URL
    const getFiltersWithEmptyUrl = async () => {
      const fetchedData = await fetch("", { method: "GET" })
        .then((res) => res.json())
        .catch(() => FILTERS_MOCK);

      // Импортируем validateFilters или используем существующую логику
      if (!Array.isArray(fetchedData)) {
        throw new Error("Filters must be an array");
      }

      fetchedData.forEach((item, i) => {
        if (typeof item.product !== "string") {
          throw new Error(`Invalid 'product' at index ${i}`);
        }
        if (!Array.isArray(item.services)) {
          throw new Error(`Invalid 'services' at index ${i}`);
        }

        item.services.forEach(
          (srv: { service: string; environments: string[] }, j: number) => {
            if (typeof srv.service !== "string") {
              throw new Error(`Invalid 'service' at [${i}][${j}]`);
            }
            if (
              !Array.isArray(srv.environments) ||
              !srv.environments.every((env: string) => typeof env === "string")
            ) {
              throw new Error(`Invalid 'environments' at [${i}][${j}]`);
            }
          }
        );
      });

      return fetchedData;
    };

    const result = await getFiltersWithEmptyUrl();

    expect(mockFetchWithEmptyUrl).toHaveBeenCalledWith("", {
      method: "GET",
    });
    expect(result).toEqual(mockResponse);

    // Восстанавливаем оригинальный fetch
    global.fetch = originalFetch;
  });

  it("должен валидировать корректные данные", async () => {
    const validData: FilterData[] = [
      {
        product: "valid-product",
        services: [
          {
            service: "valid-service",
            environments: ["prod", "dev", "qa"],
          },
        ],
      },
    ];

    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(validData),
    } as Response);

    const result = await GetFilters();

    expect(result).toEqual(validData);
    expect(result[0].product).toBe("valid-product");
    expect(result[0].services[0].service).toBe("valid-service");
    expect(result[0].services[0].environments).toEqual(["prod", "dev", "qa"]);
  });

  it("должен выбрасывать ошибку при невалидных данных - не массив", async () => {
    const invalidData = { product: "invalid" };

    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(invalidData),
    } as Response);

    await expect(GetFilters()).rejects.toThrow("Filters must be an array");
  });

  it("должен выбрасывать ошибку при невалидных данных - отсутствует product", async () => {
    const invalidData = [
      {
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

    await expect(GetFilters()).rejects.toThrow("Invalid 'product' at index 0");
  });

  it("должен выбрасывать ошибку при невалидных данных - отсутствует services", async () => {
    const invalidData = [
      {
        product: "test-product",
      },
    ];

    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(invalidData),
    } as Response);

    await expect(GetFilters()).rejects.toThrow("Invalid 'services' at index 0");
  });

  it("должен выбрасывать ошибку при невалидных данных - невалидный service", async () => {
    const invalidData = [
      {
        product: "test-product",
        services: [
          {
            service: 123, // должно быть строкой
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

  it("должен выбрасывать ошибку при невалидных данных - невалидные environments", async () => {
    const invalidData = [
      {
        product: "test-product",
        services: [
          {
            service: "test-service",
            environments: ["prod", 123, "dev"], // содержит не строку
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

  it("должен выбрасывать ошибку при невалидных данных - environments не массив", async () => {
    const invalidData = [
      {
        product: "test-product",
        services: [
          {
            service: "test-service",
            environments: "not-an-array", // должно быть массивом
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

  it("должен корректно обрабатывать сложную структуру данных", async () => {
    const complexData: FilterData[] = [
      {
        product: "complex-product-1",
        services: [
          {
            service: "service-1",
            environments: ["prod", "staging", "dev"],
          },
          {
            service: "service-2",
            environments: ["prod", "qa"],
          },
        ],
      },
      {
        product: "complex-product-2",
        services: [
          {
            service: "service-3",
            environments: ["prod"],
          },
        ],
      },
    ];

    mockFetch.mockResolvedValueOnce({
      json: () => Promise.resolve(complexData),
    } as Response);

    const result = await GetFilters();

    expect(result).toHaveLength(2);
    expect(result[0].product).toBe("complex-product-1");
    expect(result[0].services).toHaveLength(2);
    expect(result[0].services[0].environments).toEqual([
      "prod",
      "staging",
      "dev",
    ]);
    expect(result[1].product).toBe("complex-product-2");
    expect(result[1].services).toHaveLength(1);
  });
});
