import { createSlice, type PayloadAction } from "@reduxjs/toolkit";
import { wsRegistry } from "@/lib/model/wsRegistry";

interface AnalysisParams {
  filters: {
    start_date: string;
    end_date: string;
    service: string;
    product?: string;
    environment?: string;
  };
  prompt: string;
}

interface LogExplainState {
  isAnalysisActive: boolean;
  analysisParams: AnalysisParams | null;
}

const LOG_EXPLAIN_PERSIST_KEY = "logExplainState";

function loadInitialState(): LogExplainState {
  try {
    if (typeof window !== "undefined" && window.localStorage) {
      const raw = localStorage.getItem(LOG_EXPLAIN_PERSIST_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<LogExplainState>;
        return {
          isAnalysisActive: Boolean(parsed.isAnalysisActive),
          analysisParams: parsed.analysisParams ?? null,
        };
      }
    }
  } catch {
    // ignore
  }
  return { isAnalysisActive: false, analysisParams: null };
}

const initialState: LogExplainState = loadInitialState();

const logExplainSlice = createSlice({
  name: "logExplain",
  initialState,
  reducers: {
    startAnalysis: (state, action: PayloadAction<AnalysisParams>) => {
      state.isAnalysisActive = true;
      state.analysisParams = action.payload;
    },
    clearAnalysisParams: (state) => {
      state.analysisParams = null;
    },
    resetAnalysis: (state) => {
      // Close all sockets and reset view state back to form
      wsRegistry.clear();
      state.isAnalysisActive = false;
      state.analysisParams = null;
    },
  },
});

export const { startAnalysis, clearAnalysisParams, resetAnalysis } =
  logExplainSlice.actions;
export default logExplainSlice.reducer;
