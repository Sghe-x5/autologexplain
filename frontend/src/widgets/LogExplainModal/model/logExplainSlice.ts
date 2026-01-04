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

const initialState: LogExplainState = {
  isAnalysisActive: false,
  analysisParams: null,
};

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
