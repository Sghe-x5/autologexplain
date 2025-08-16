import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { wsRegistry } from "@/lib/model/wsRegistry";
import type { ChatData, TServerMsg } from "@/lib/chat.schemas";
import { WS_BASE } from "@/consts/api.const";

type UpdateCachedData = (recipe: (draft: ChatData) => void) => void;

function handleChatMessage(
  msg: TServerMsg,
  updateCachedData: UpdateCachedData
) {
  updateCachedData((draft: ChatData) => {
    if (!draft.items) draft.items = [];
    if (msg.type === "final") {
      draft.items.push({
        role: "assistant",
        id: msg.message_id,
        requestId: msg.request_id,
        text: msg.content,
        pending: false,
      });
    }
  });
}

export const chatWebSocketApi = createApi({
  reducerPath: "chatWebSocketApi",
  baseQuery: fetchBaseQuery({ baseUrl: WS_BASE }),
  tagTypes: ["ChatStream"],
  endpoints: (build) => ({
    streamChat: build.query<
      ChatData,
      { chatId: string; token: string; wsUrl: string }
    >({
      queryFn: () => ({
        data: { chatId: "", connected: false, items: [], pending: {} },
      }),

      async onCacheEntryAdded(arg, { updateCachedData, cacheEntryRemoved }) {
        const { chatId, token, wsUrl } = arg;
        const fullUrl = `${wsUrl.replace(
          /\/$/,
          ""
        )}/ws/chats/${chatId}?token=${encodeURIComponent(token)}`;
        const ws = new WebSocket(fullUrl);
        wsRegistry.set(chatId, ws);

        ws.addEventListener("open", () => {
          updateCachedData((draft) => {
            draft.connected = true;
          });
        });

        ws.addEventListener("message", (event) => {
          handleChatMessage(JSON.parse(event.data), updateCachedData);
        });

        ws.addEventListener("close", () => {
          wsRegistry.del(chatId);
          updateCachedData((draft) => {
            draft.connected = false;
          });
        });

        await cacheEntryRemoved;
        ws.close();
        wsRegistry.del(chatId);
      },
    }),
  }),
});

export const { useStreamChatQuery } = chatWebSocketApi;
