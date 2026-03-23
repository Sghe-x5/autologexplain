import { describe, it, expect } from "vitest";
import { logFormSchema } from "../../../widgets/LogExplainModal/model/types";

describe("logFormSchema", () => {
  const baseValid = {
    product: "test-product",
    service: "auth",
    environment: "prod",
    startTime: new Date("2023-01-01"),
    endTime: new Date("2023-01-02"),
  };

  it("должен принимать валидные данные", () => {
    const result = logFormSchema.safeParse(baseValid);
    expect(result.success).toBe(true);
  });

  it("должна быть ошибка если не выбран продукт", () => {
    const result = logFormSchema.safeParse({ ...baseValid, product: "" });
    expect(result.success).toBe(false);
  });

  it("должна быть ошибка если не выбран сервис", () => {
    const result = logFormSchema.safeParse({ ...baseValid, service: "" });
    expect(result.success).toBe(false);
  });

  it("должна быть ошибка если не выбрано окружение", () => {
    const result = logFormSchema.safeParse({ ...baseValid, environment: "" });
    expect(result.success).toBe(false);
  });

  it("должна быть ошибка если время старта больше времени конца", () => {
    const result = logFormSchema.safeParse({
      ...baseValid,
      startTime: new Date("2023-01-03"),
      endTime: new Date("2023-01-02"),
    });
    expect(result.success).toBe(false);
  });

  it("должна быть ошибка если время старта в будущем", () => {
    const result = logFormSchema.safeParse({
      ...baseValid,
      startTime: new Date("2999-01-01"),
    });
    expect(result.success).toBe(false);
  });

  it("должна быть ошибка если ремя конца в будущем", () => {
    const result = logFormSchema.safeParse({
      ...baseValid,
      endTime: new Date("2999-01-01"),
    });
    expect(result.success).toBe(false);
  });
});
