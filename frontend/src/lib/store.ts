import { configureStore } from "@reduxjs/toolkit";

import showModal from "@/widgets/LogExplainModal/model/showModalSlice";

export const store = configureStore({
  reducer: {
    showModal: showModal,
  },
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
