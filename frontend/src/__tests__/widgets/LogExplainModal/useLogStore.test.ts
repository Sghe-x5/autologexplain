import { describe, it, expect, vi } from "vitest";
import { useLogStore } from "../../../widgets/LogExplainModal/model/store";
import { wsRegistry } from "@/lib/model/wsRegistry";

describe("useLogStore", () => {
  it("проверка получения логов", () => {
    const log = { userId: 1, service: "auth", period: null, visits: 5, sessionDurationSeconds: 120, sessionDurationReadable: "2m", purchases: { count: 1, totalAmount: 100 }, refunds: { count: 0, totalAmount: 0 }, summary: "ok" };
    useLogStore.getState().setLog(log);
    expect(useLogStore.getState().log).toEqual(log);
  });

  it("проверка очистки параметров", () => {
    const params = { filters: { start_date: "2023-01-01", end_date: "2023-01-02", service: "auth" }, prompt: "analyze" };
    useLogStore.getState().setAnalysisParams(params);
    expect(useLogStore.getState().analysisParams).toEqual(params);

    useLogStore.getState().clearAnalysisParams();
    expect(useLogStore.getState().analysisParams).toBeNull();
  });

  it("проверка сброса хранилища и очистки Regestry", () => {
    const spy = vi.spyOn(wsRegistry, "clear").mockImplementation(() => {});
    useLogStore.getState().reset();
    expect(useLogStore.getState().log).toBeNull();
    expect(useLogStore.getState().analysisParams).toBeNull();
    expect(spy).toHaveBeenCalled();
  });
});