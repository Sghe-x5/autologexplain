import { describe, it, expect, vi } from "vitest";

// Простой пример теста для демонстрации
describe("Примеры тестирования", () => {
  it("должен демонстрировать базовые assertions", () => {
    expect(2 + 2).toBe(4);
    expect("hello").toBe("hello");
    expect([1, 2, 3]).toHaveLength(3);
    expect({ name: "test" }).toEqual({ name: "test" });
  });

  it("должен демонстрировать мокирование функций", () => {
    const mockFunction = vi.fn();
    mockFunction.mockReturnValue("mocked value");

    expect(mockFunction()).toBe("mocked value");
    expect(mockFunction).toHaveBeenCalledTimes(1);
  });

  it("должен демонстрировать async тесты", async () => {
    const asyncFunction = async () => {
      return new Promise<string>((resolve) => {
        setTimeout(() => resolve("async result"), 10);
      });
    };

    const result = await asyncFunction();
    expect(result).toBe("async result");
  });

  it("должен демонстрировать тестирование исключений", () => {
    const functionThatThrows = () => {
      throw new Error("Test error");
    };

    expect(() => functionThatThrows()).toThrow("Test error");
  });
});
