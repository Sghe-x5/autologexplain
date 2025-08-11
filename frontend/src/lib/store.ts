import { configureStore } from "@reduxjs/toolkit";

import showModal from "@/widgets/LogExplainModal/model/showModalSlice";
import { chatApi } from "@/widgets/LogExplainModal/model/WebSocket/chat.api";

export const store = configureStore({
  reducer: {
    showModal: showModal,
    [chatApi.reducerPath]: chatApi.reducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware().concat(chatApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
