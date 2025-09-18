import * as z from "zod";

// server -> client
export const Ready = z.object({
  type: z.literal("ready"),
  chat_id: z.string(),
});
export const Accepted = z.object({
  type: z.literal("accepted"),
  request_id: z.string().uuid(),
});
export const Final = z.object({
  type: z.literal("final"),
  request_id: z.string().uuid(),
  message_id: z.string().uuid(),
  content: z.string(),
});
export const ErrorMsg = z.object({
  type: z.literal("error"),
  code: z.string(),
  message: z.string().optional(),
});

export const ServerMsg = z.union([Ready, Accepted, Final, ErrorMsg]);
export type TServerMsg = z.infer<typeof ServerMsg>;

// client -> server
export const AnalysisStart = z.object({
  type: z.literal("analysis_start"),
  request_id: z.string().uuid(),
  filters: z.object({
    start_date: z.string(),
    end_date: z.string(),
    service: z.string(),
  }),
  prompt: z.string(),
});

export const ChatTurn = z.object({
  type: z.literal("chat_turn"),
  request_id: z.string().ulid(),
  content: z.string().min(1),
});
export type TOutgoing =
  | z.infer<typeof AnalysisStart>
  | z.infer<typeof ChatTurn>;

// модель UI/кэша
export type ChatItem =
  | { role: "user"; id: string; text: string }
  | {
      role: "assistant";
      id: string;
      text: string;
      requestId: string;
      pending: boolean;
    };

export type ChatData = {
  chatId: string;
  connected: boolean;
  items: ChatItem[];
  pending: Record<string, unknown>;
};

export type ConversationState = {
  chatId: string;
  connected: boolean;
  items: ChatItem[];
  pending: Record<string, true>;
};
