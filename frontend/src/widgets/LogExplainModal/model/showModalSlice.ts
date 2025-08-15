import { createSlice } from "@reduxjs/toolkit";

interface CounterState {
  isShown: boolean;
}

const initialState: CounterState = { isShown: false };

const showModalSlice = createSlice({
  name: "showModal",
  initialState,
  reducers: {
    open: (state) => {
      state.isShown = true;
    },
    close: (state) => {
      state.isShown = false;
    },
  },
});

export const { open, close } = showModalSlice.actions;
export default showModalSlice.reducer;
