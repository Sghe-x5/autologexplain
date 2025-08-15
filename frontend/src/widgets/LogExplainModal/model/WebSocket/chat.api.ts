import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { wsRegistry } from "./wsRegistry";

type NewChatResp = { chat_id: string; token: string };
type RenewResp = { token: string };

export type ChatItem = {
  role: string;
  id: string;
  requestId: string;
  text: string;
  pending: boolean;
};

type ChatData = {
  chatId: string;
  connected: boolean;
  items: ChatItem[];
  pending: Record<string, unknown>;
};

export const chatApi = createApi({
  reducerPath: "chatApi",
  baseQuery: fetchBaseQuery({ baseUrl: "http://localhost:8080" }),
  tagTypes: ["Conversation"],
  endpoints: (build) => ({
    newChat: build.mutation<NewChatResp, void>({
      query: () => ({ url: "/chats/new", method: "POST" }),
    }),

    renewToken: build.mutation<RenewResp, { chatId: string }>({
      query: ({ chatId }) => ({
        url: "/chats/renew",
        method: "POST",
        body: { chat_id: chatId },
      }),
    }),

    streamChat: build.query<
      ChatData,
      { chatId: string; token: string; wsUrl: string }
    >({
      queryFn: () => ({
        data: { chatId: "", connected: false, items: [], pending: {} },
      }),

      async onCacheEntryAdded(arg, { updateCachedData, cacheEntryRemoved }) {
        const { chatId, token, wsUrl } = arg;
        const ws = new WebSocket(
          `${wsUrl.replace(
            /\/$/,
            ""
          )}/ws/chats/${chatId}?token=${encodeURIComponent(token)}`
        );
        wsRegistry.set(chatId, ws);

        ws.addEventListener("open", () => {
          console.log("WS connected");
          updateCachedData((draft) => {
            draft.connected = true;
          });
        });

        ws.addEventListener("message", (event) => {
          const msg = JSON.parse(event.data);
          console.log("WS message:", msg);

          updateCachedData((draft) => {
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
            // Добавь обработку других типов сообщений по необходимости
          });
        });

        ws.addEventListener("close", () => {
          wsRegistry.del(chatId);
          console.log("WS disconnected");
          updateCachedData((draft) => {
            draft.connected = false;
          });
        });

        await cacheEntryRemoved;
        ws.close();
        wsRegistry.del(chatId);
      },
    }),

    analysisStart: build.mutation<
      { enqueued: true; request_id: string },
      {
        chatId: string;
        payload: {
          filters: { start_date: string; end_date: string; service: string };
          prompt: string;
        };
      }
    >({
      async queryFn({ chatId, payload }) {
        const ws = wsRegistry.get(chatId);
        if (!ws || ws.readyState !== WebSocket.OPEN) {
          return {
            error: {
              status: "CUSTOM_ERROR",
              error: "WebSocket connection closed",
            },
          };
        }

        const request_id = crypto.randomUUID();

        ws.send(
          JSON.stringify({
            type: "analysis_start",
            request_id,
            filters: payload.filters,
            prompt: payload.prompt,
          })
        );

        return { data: { enqueued: true, request_id } };
      },
    }),

    chatTurn: build.mutation<
      { enqueued: true; request_id: string },
      { chatId: string; content: string }
    >({
      async queryFn({ chatId, content }) {
        const ws = wsRegistry.get(chatId);
        if (!ws || ws.readyState !== WebSocket.OPEN)
          return {
            error: {
              status: "CUSTOM_ERROR",
              error: "WebSocket connection closed",
            },
          };

        const request_id = crypto.randomUUID();
        ws.send(JSON.stringify({ type: "chat_turn", request_id, content }));

        return { data: { enqueued: true, request_id } };
      },
    }),
  }),
});

export const {
  useNewChatMutation,
  useRenewTokenMutation,
  useStreamChatQuery,
  useAnalysisStartMutation,
  useChatTurnMutation,
} = chatApi;
