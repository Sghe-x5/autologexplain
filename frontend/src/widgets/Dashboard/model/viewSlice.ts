import { createSlice, type PayloadAction } from "@reduxjs/toolkit";

export type DashboardView = "overview" | "incidents" | "graph" | "metrics";

interface ViewState {
  view: DashboardView;
  selectedIncidentId: string | null;
}

const initial: ViewState = { view: "overview", selectedIncidentId: null };

const viewSlice = createSlice({
  name: "dashboardView",
  initialState: initial,
  reducers: {
    setView(state, action: PayloadAction<DashboardView>) {
      state.view = action.payload;
      if (action.payload !== "incidents") {
        state.selectedIncidentId = null;
      }
    },
    selectIncident(state, action: PayloadAction<string | null>) {
      state.selectedIncidentId = action.payload;
    },
  },
});

export const { setView, selectIncident } = viewSlice.actions;
export default viewSlice.reducer;
