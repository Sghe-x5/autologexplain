import { baseUrl } from "@/consts/api.const";
import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";

type NewChatResp = { chat_id: string; token: string };
type RenewResp = { token: string };

export const chatManagementApi = createApi({
  reducerPath: "chatManagementApi",
  baseQuery: fetchBaseQuery({ baseUrl: baseUrl }),
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
