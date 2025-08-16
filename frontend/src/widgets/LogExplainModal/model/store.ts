import { create } from "zustand";
import type { UserLogExplanation } from "./types";
import { wsRegistry } from "@/lib/model/wsRegistry";

interface AnalysisParams {
  filters: { start_date: string; end_date: string; service: string };
  prompt: string;
}

interface LogStore {
  log: UserLogExplanation | null;
  analysisParams: AnalysisParams | null;
  setLog: (log: UserLogExplanation) => void;
  setAnalysisParams: (params: AnalysisParams) => void;
  clearAnalysisParams: () => void;
  reset: () => void;
}

export const useLogStore = create<LogStore>((set) => ({
  log: null,
  analysisParams: null,
  setLog: (log) => set({ log }),
  setAnalysisParams: (params) => set({ analysisParams: params }),
  clearAnalysisParams: () => set({ analysisParams: null }),
  reset: () => {
    // Очищаем все WebSocket соединения при сбросе
    console.log("Clearing all WebSocket connections on reset");
    wsRegistry.clear();
    set({ log: null, analysisParams: null });
  },
}));
