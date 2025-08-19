import { useEffect, useMemo, useRef, useState } from "react";
import { WS_BASE } from "@/consts/api.const";
import type { ChatItem } from "@/lib/chat.schemas";
import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/lib/store";
import { clearAnalysisParams as clearAnalysisParamsAction } from "../../../model/logExplainSlice";
import { wsRegistry } from "@/lib/model/wsRegistry";
import {
  useChatTurnMutation,
  useNewChatMutation,
  useStreamChatQuery,
  useAutoAnalysisMutation,
} from "@/api";

// ключи для localStorage / cookie
const LS_MESSAGES_KEY = "chat_messages";
const COOKIE_CHAT_KEY = "chat_session"; // chat_id + token JSON
const EPHEMERAL_START_TEXT = "Начинаю анализ логов...";
const EPHEMERAL_START_ID = "analysis-start";

// утилита работы с куками
function setCookie(name: string, value: string, days = 7) {
  const d = new Date();
  d.setTime(d.getTime() + days * 24 * 60 * 60 * 1000);
  document.cookie = `${name}=${value};expires=${d.toUTCString()};path=/`;
}
function getCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp("(^| )" + name + "=([^;]+)"));
  return match ? decodeURIComponent(match[2]) : null;
}
function deleteCookie(name: string) {
  document.cookie = `${name}=; Max-Age=0; path=/`;
}

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
  // при инициализации — восстанавливаем состояние
  const [messages, setMessages] = useState<ChatItem[]>(() => {
    const saved = localStorage.getItem(LS_MESSAGES_KEY);
    return saved ? (JSON.parse(saved) as ChatItem[]) : [];
  });

  const [input, setInput] = useState("");
  const [newChat] = useNewChatMutation();
  const [chatTurn, { isLoading: isSending }] = useChatTurnMutation();
  const [autoAnalysis] = useAutoAnalysisMutation();
  const [isInitializing, setIsInitializing] = useState(false);
  const dispatch = useDispatch<AppDispatch>();
  const isAnalysisActive = useSelector(
    (state: RootState) => state.logExplain.isAnalysisActive
  );

  const [chat, setChat] = useState<{ chatId: string; token: string } | null>(
    () => {
      const cookie = getCookie(COOKIE_CHAT_KEY);
      return cookie ? JSON.parse(cookie) : null;
    }
  );

  const [isAssistantTyping, setIsAssistantTyping] = useState(false);

  const initializationRef = useRef(false);
  const seenIdsRef = useRef<Set<string>>(new Set());

  // сохраняем messages в localStorage (без эфемерного стартового сообщения)
  useEffect(() => {
    const toSave = messages.filter((m) => m.id !== EPHEMERAL_START_ID);
    localStorage.setItem(LS_MESSAGES_KEY, JSON.stringify(toSave));
  }, [messages]);

  // сохраняем chat в cookie
  useEffect(() => {
    if (chat) {
      setCookie(COOKIE_CHAT_KEY, JSON.stringify(chat));
    }
  }, [chat]);

  // при размонтировании закрываем ws
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

  // сброс состояния только если нет активного анализа и нет чата
  useEffect(() => {
    if (autoAnalysisParams === undefined && !isAnalysisActive && !chat) {
      setMessages([]);
      localStorage.removeItem(LS_MESSAGES_KEY);
      setInput("");
      initializationRef.current = false;
      setIsInitializing(false);
      seenIdsRef.current = new Set();
    }
  }, [autoAnalysisParams, isAnalysisActive, chat]);

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
              id: EPHEMERAL_START_ID,
              role: "assistant",
              text: EPHEMERAL_START_TEXT,
            } as ChatItem,
          ]);
          seenIdsRef.current.add(EPHEMERAL_START_ID);
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
        const hasAssistant = fresh.some((m) => m.role === "assistant");
        if (hasAssistant) {
          setIsAssistantTyping(false);
        }
        setMessages((prev) => {
          const base = hasAssistant
            ? prev.filter((m) => m.id !== EPHEMERAL_START_ID)
            : prev;
          return [...base, ...fresh];
        });
      }
    }
  }, [data]);

  const sendMessage = async () => {
    if (!chat || !input.trim()) return;

    const text = input.trim();
    setInput("");

    setMessages((prev) => [
      ...prev,
      { id: crypto.randomUUID(), role: "user", text },
    ]);

    setIsAssistantTyping(true);

    try {
      await chatTurn({ chatId: chat.chatId, content: text });
    } catch {
      setIsAssistantTyping(false);
    }
  };

  // очищение для нового чата
  const resetChat = () => {
    setMessages([]);
    setChat(null);
    deleteCookie(COOKIE_CHAT_KEY);
    localStorage.removeItem(LS_MESSAGES_KEY);
    seenIdsRef.current.clear();
  };

  return {
    messages,
    input,
    isAssistantTyping,
    isSending,
    setInput,
    sendMessage,
    resetChat, // вот тут точка, чтобы "забыть" старый чат
  } as const;
}
