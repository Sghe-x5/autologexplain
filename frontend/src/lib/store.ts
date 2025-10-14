import { configureStore } from "@reduxjs/toolkit";

import showModal from "@/widgets/LogExplainModal/model/showModalSlice";
import logExplain from "@/widgets/LogExplainModal/model/logExplainSlice";
import {
  chatManagementApi,
  chatMessagesApi,
  chatWebSocketApi,
  wsApi,
} from "@/api";


export const store = configureStore({
  reducer: {
    showModal,
    logExplain,
    [wsApi.reducerPath]: wsApi.reducer,
    [chatManagementApi.reducerPath]: chatManagementApi.reducer,
    [chatWebSocketApi.reducerPath]: chatWebSocketApi.reducer,
    [chatMessagesApi.reducerPath]: chatMessagesApi.reducer,
  },
  // preloadedState берём из самого слайса (он читает localStorage сам)
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware()
      .concat(wsApi.middleware)
      .concat(chatManagementApi.middleware)
      .concat(chatWebSocketApi.middleware)
      .concat(chatMessagesApi.middleware),
});

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
