import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { wsRegistry } from "@/lib/model/wsRegistry";
import { WS_BASE } from "@/lib/consts";

function sendWebSocketMessage(chatId: string, message: any) {
  const ws = wsRegistry.get(chatId);
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    return {
      error: {
        status: "CUSTOM_ERROR" as const,
        error: "WebSocket connection closed",
      },
    };
  }

  ws.send(JSON.stringify(message));
  return {
    data: { enqueued: true as const, request_id: message.request_id as string },
  };
}

export const chatMessagesApi = createApi({
  reducerPath: "chatMessagesApi",
  baseQuery: fetchBaseQuery({ baseUrl: WS_BASE }),
  tagTypes: ["ChatMessage"],
  endpoints: (build) => ({
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
        return sendWebSocketMessage(chatId, {
          type: "analysis_start",
          request_id: crypto.randomUUID(),
          filters: payload.filters,
          prompt: payload.prompt,
        });
      },
    }),

    chatTurn: build.mutation<
      { enqueued: true; request_id: string },
      { chatId: string; content: string }
    >({
      async queryFn({ chatId, content }) {
        return sendWebSocketMessage(chatId, {
          type: "chat_turn",
          request_id: crypto.randomUUID(),
          content,
        });
      },
    }),
  }),
});

export const { useAnalysisStartMutation, useChatTurnMutation } =
  chatMessagesApi;
