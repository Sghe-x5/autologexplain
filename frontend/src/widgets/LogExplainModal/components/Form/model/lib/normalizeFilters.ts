import type { FilterData } from "@/api/getFilters";

export function buildFiltersByProduct(filters: FilterData[]) {
  return new Map(filters.map((f) => [f.product, f] as const));
}
