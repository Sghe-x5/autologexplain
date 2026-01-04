import { create } from "zustand";
import type { UserLogExplanation } from "./types";

interface LogStore {
  log: UserLogExplanation | null;
  setLog: (log: UserLogExplanation) => void;
  reset: () => void;
}

export const useLogStore = create<LogStore>((set) => ({
  log: null,
  setLog: (log) => set({ log }),
  reset: () => set({ log: null }),
}));
