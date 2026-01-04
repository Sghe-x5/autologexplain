import { validateFilters, type FilterData } from "@/api/getFilters";
import { describe, it, expect } from "vitest";

describe("validateFilters (unit)", () => {
  it("пропускает корректный массив FilterData", () => {
    const data: FilterData[] = [
      {
        product: "p1",
        services: [
          { service: "s1", environments: ["dev", "prod"] },
          { service: "s2", environments: [] },
        ],
      },
    ];

    expect(() => validateFilters(data)).not.toThrow();
  });

  it("кидает если data не массив", () => {
    expect(() => validateFilters({} as any)).toThrow(
      "Filters must be an array"
    );
  });

  it("кидает если product не строка", () => {
    const invalid = [{ product: 123, services: [] }];
    expect(() => validateFilters(invalid as any)).toThrow(
      "Invalid 'product' at index 0"
    );
  });

  it("кидает если services не массив", () => {
    const invalid = [{ product: "p", services: {} }];
    expect(() => validateFilters(invalid as any)).toThrow(
      "Invalid 'services' at index 0"
    );
  });

  it("кидает если service не строка", () => {
    const invalid = [
      { product: "p", services: [{ service: 42, environments: [] }] },
    ];
    expect(() => validateFilters(invalid as any)).toThrow(
      "Invalid 'service' at [0][0]"
    );
  });

  it("кидает если environments не массив строк", () => {
    const invalid = [
      { product: "p", services: [{ service: "s", environments: [123] }] },
    ];
    expect(() => validateFilters(invalid as any)).toThrow(
      "Invalid 'environments' at [0][0]"
    );
  });
});
