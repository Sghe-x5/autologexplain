import { useEffect, useMemo, useRef, useState } from "react";
import { WS_BASE } from "@/consts/api.const";
import type { ChatItem } from "@/lib/chat.schemas";
import { useDispatch } from "react-redux";
import type { AppDispatch } from "@/lib/store";
import { clearAnalysisParams as clearAnalysisParamsAction } from "../../../model/logExplainSlice";
import { wsRegistry } from "@/lib/model/wsRegistry";
import {
  useChatTurnMutation,
  useNewChatMutation,
  useStreamChatQuery,
  useAutoAnalysisMutation,
} from "@/api";

export interface UseChatWithAIParams {
  autoAnalysisParams?: {
    filters: {
      start_date: string;
      end_date: string;
      service: string;
      product?: string;
      environment?: string;
    };
    prompt: string;
  };
}

export function useChatWithAI({ autoAnalysisParams }: UseChatWithAIParams) {
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [input, setInput] = useState("");
  const [newChat] = useNewChatMutation();
  const [chatTurn, { isLoading: isSending }] = useChatTurnMutation();
  const [autoAnalysis] = useAutoAnalysisMutation();
  const [isInitializing, setIsInitializing] = useState(false);
  const dispatch = useDispatch<AppDispatch>();

  const [chat, setChat] = useState<{ chatId: string; token: string } | null>(
    null
  );

  const [isAssistantTyping, setIsAssistantTyping] = useState(false);

  const initializationRef = useRef(false);
  const seenIdsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    return () => {
      if (chat) {
        const ws = wsRegistry.get(chat.chatId);
        if (ws) {
          ws.close();
          wsRegistry.del(chat.chatId);
        }
      }
    };
  }, [chat]);

  useEffect(() => {
    if (autoAnalysisParams === undefined) {
      setMessages([]);
      setInput("");
      initializationRef.current = false;
      setIsInitializing(false);
      seenIdsRef.current = new Set();
    }
  }, [autoAnalysisParams]);

  useEffect(() => {
    if (autoAnalysisParams !== undefined) {
      initializationRef.current = false;
    }

    if (initializationRef.current) return;

    if (autoAnalysisParams && !chat && !isInitializing) {
      initializationRef.current = true;
      setIsInitializing(true);

      (async () => {
        try {
          const result = await autoAnalysis().unwrap();
          setChat({ chatId: result.chatId, token: result.token });

          setMessages([
            {
              id: crypto.randomUUID(),
              role: "assistant",
              text: "Начинаю анализ логов...",
            } as ChatItem,
          ]);
          seenIdsRef.current.add("analysis-start");

          setIsAssistantTyping(true);
        } catch {
          setMessages([
            {
              id: crypto.randomUUID(),
              role: "assistant",
              text: "Ошибка при запуске анализа логов. Попробуйте еще раз.",
            } as ChatItem,
          ]);
        } finally {
          setIsInitializing(false);
        }
      })();
    } else if (!autoAnalysisParams && !chat && !isInitializing) {
      initializationRef.current = true;
      setIsInitializing(true);

      (async () => {
        try {
          const res = await newChat().unwrap();
          setChat({ chatId: res.chat_id, token: res.token });
        } catch (error) {
          console.error("Failed to create chat:", error);
        } finally {
          setIsInitializing(false);
        }
      })();
    }
  }, [autoAnalysisParams, chat, autoAnalysis, newChat, isInitializing]);

  const streamParams = useMemo(
    () =>
      chat ? { chatId: chat.chatId, token: chat.token, wsUrl: WS_BASE } : null,
    [chat]
  );

  const { data } = useStreamChatQuery(streamParams!, { skip: !chat });

  useEffect(() => {
    if (chat && autoAnalysisParams && data?.connected) {
      const ws = wsRegistry.get(chat.chatId);
      if (ws && ws.readyState === WebSocket.OPEN) {
        const message = {
          type: "analysis_start",
          request_id: crypto.randomUUID(),
          filters: autoAnalysisParams.filters,
          prompt: autoAnalysisParams.prompt,
        };
        ws.send(JSON.stringify(message));
        setIsAssistantTyping(true);
        dispatch(clearAnalysisParamsAction());
      }
    }
  }, [chat, autoAnalysisParams, data?.connected, dispatch]);

  useEffect(() => {
    if (data?.items?.length) {
      const seen = seenIdsRef.current;
      const fresh = data.items
        .filter((m: ChatItem) => !seen.has(m.id))
        .map((m: ChatItem) => ({
          ...m,
          text: m.text
            .replace(/^```json\n/, "")
            .replace(/\n```$/, "")
            .replace(/Запрос: .*/, ""),
        }));

      if (fresh.length) {
        fresh.forEach((m) => seen.add(m.id));
        if (fresh.some((m) => m.role === "assistant")) {
          setIsAssistantTyping(false);
        }
        setMessages((prev) => [...prev, ...fresh]);
      }
    }
  }, [data]);

  const sendMessage = async () => {
    if (!chat || !input.trim()) return;

    const text = input.trim();
    setInput("");

    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", text } as ChatItem,
    ]);

    setIsAssistantTyping(true);

    try {
      await chatTurn({ chatId: chat.chatId, content: text });
    } catch {
      setIsAssistantTyping(false);
    }
  };

  return {
    messages,
    input,
    isAssistantTyping,
    isSending,
    setInput,
    sendMessage,
  } as const;
}
