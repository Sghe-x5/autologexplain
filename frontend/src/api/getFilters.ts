import { FILTER_URL } from "@/consts/api.const";

export type FilterData = {
  product: string;
  services: {
    service: string;
    environments: string[];
  }[];
};

export function validateFilters(data: unknown): asserts data is FilterData[] {
  if (!Array.isArray(data)) {
    throw new Error("Filters must be an array");
  }

  data.forEach((item, i) => {
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
}

export const GetFilters = async (): Promise<FilterData[]> => {
  const fetchedData = await fetch(FILTER_URL || "", { method: "GET" })
    .then((res) => res.json())
    .catch(() => ({
      message: "rejected promise", // Заменить в проде
    }));

  validateFilters(fetchedData);

  return fetchedData;
};
