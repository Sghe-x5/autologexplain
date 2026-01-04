import { configureStore } from "@reduxjs/toolkit";

import showModal from "@/widgets/LogExplainModal/model/showModalSlice";
import logExplain from "@/widgets/LogExplainModal/model/logExplainSlice";
import {
  chatManagementApi,
  chatMessagesApi,
  chatWebSocketApi,
  wsApi,
} from "@/api";

const LOG_EXPLAIN_PERSIST_KEY = "logExplainState";

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

// persist logExplain slice
try {
  store.subscribe(() => {
    const state = store.getState() as { logExplain: unknown };
    try {
      localStorage.setItem(
        LOG_EXPLAIN_PERSIST_KEY,
        JSON.stringify(state.logExplain)
      );
    } catch {
      // ignore quota or serialization issues
    }
  });
} catch {
  // ignore environments without localStorage
}

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;
