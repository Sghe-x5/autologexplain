import { baseUrl } from "@/consts/api.const";
import { createApi, type BaseQueryFn } from "@reduxjs/toolkit/query/react";

type NewChatResp = { chat_id: string; token: string };
type RenewResp = { token: string };

type ChatRequest = {
  url: string;
  method?: string;
  body?: unknown;
};

type ChatError = {
  status: number | "FETCH_ERROR";
  data: unknown;
};

async function readResponseBody(response: Response) {
  const text = await response.text();
  if (!text) return undefined;

  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

const chatBaseQuery: BaseQueryFn<ChatRequest, unknown, ChatError> = async ({
  url,
  method = "GET",
  body,
}) => {
  try {
    const response = await fetch(`${baseUrl}${url}`, {
      method,
      headers:
        body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    });

    const data = await readResponseBody(response);

    if (!response.ok) {
      return { error: { status: response.status, data } };
    }

    return { data };
  } catch (error) {
    return {
      error: {
        status: "FETCH_ERROR",
        data: error instanceof Error ? error.message : String(error),
      },
    };
  }
};

export const chatManagementApi = createApi({
  reducerPath: "chatManagementApi",
  baseQuery: chatBaseQuery,
  tagTypes: ["Chat"],
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
  }),
});

export const { useNewChatMutation, useRenewTokenMutation } = chatManagementApi;
