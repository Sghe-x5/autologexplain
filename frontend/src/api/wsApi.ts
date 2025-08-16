import { WS_BASE } from "@/consts/api.const";
import type { TServerMsg } from "@/lib/chat.schemas";
import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

export const wsApi = createApi({
  reducerPath: "wsApi",
  baseQuery: fetchBaseQuery({ baseUrl: WS_BASE }),
  tagTypes: ["WebSocket"],
  endpoints: (build) => ({
    createWebSocket: build.query<
      { connected: boolean; ws: WebSocket | null },
      {
        url: string;
        onMessage?: (msg: TServerMsg) => void;
        onOpen?: () => void;
        onClose?: () => void;
      }
    >({
      queryFn: () => ({ data: { connected: false, ws: null } }),
      async onCacheEntryAdded(arg, { updateCachedData, cacheEntryRemoved }) {
        const { url, onMessage, onOpen, onClose } = arg;
        const ws = new WebSocket(url);

        ws.addEventListener("open", () => {
          updateCachedData((draft) => {
            draft.connected = true;
            draft.ws = ws;
          });
          onOpen?.();
        });

        ws.addEventListener("message", (event) => {
          onMessage?.(JSON.parse(event.data));
        });

        ws.addEventListener("close", () => {
          updateCachedData((draft) => {
            draft.connected = false;
          });
          onClose?.();
        });

        await cacheEntryRemoved;
        ws.close();
      },
    }),
  }),
});

export const { useCreateWebSocketQuery } = wsApi;
