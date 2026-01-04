import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { wsRegistry } from "@/lib/model/wsRegistry";
import { WS_BASE, baseUrl } from "@/consts/api.const";

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

    autoAnalysis: build.mutation<
      { chatId: string; token: string; request_id: string },
      void
    >({
      async queryFn() {
        console.log("Creating new chat...");
        const newChatResponse = await fetch(`${baseUrl}/chats/new`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (!newChatResponse.ok) {
          const errorText = await newChatResponse.text();
          console.error(
            "Failed to create chat:",
            newChatResponse.status,
            errorText
          );
          throw new Error(
            `Failed to create chat: ${newChatResponse.status} ${errorText}`
          );
        }

        const { chat_id, token } = await newChatResponse.json();
        console.log("Chat created successfully:", { chat_id, token });

        // Возвращаем параметры чата, WebSocket соединение будет установлено в ChatWithAI
        return {
          data: {
            chatId: chat_id,
            token,
            request_id: crypto.randomUUID(),
          },
        };
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

export const {
  useAnalysisStartMutation,
  useChatTurnMutation,
  useAutoAnalysisMutation,
} = chatMessagesApi;
