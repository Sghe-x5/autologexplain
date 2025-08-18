import { Input } from "@/components/ui/input";
import Button from "@/components/ui/button/button";
import { Bot } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

import { useEffect, useMemo, useState, useRef } from "react";
import { WS_BASE } from "@/consts/api.const";
import type { ChatItem } from "@/lib/chat.schemas";
import {
  useChatTurnMutation,
  useNewChatMutation,
  useStreamChatQuery,
  useAutoAnalysisMutation,
} from "@/api";
import { wsRegistry } from "@/lib/model/wsRegistry";
import { useDispatch } from "react-redux";
import type { AppDispatch } from "@/lib/store";
import { clearAnalysisParams as clearAnalysisParamsAction } from "../model/logExplainSlice";

interface ChatWithAIProps {
  autoAnalysisParams?: {
    filters: { start_date: string; end_date: string; service: string };
    prompt: string;
  };
}

const TypingIndicator = () => (
  <div className="flex gap-1 items-center text-gray-500 px-3 py-2">
    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
  </div>
);

export const ChatWithAI = ({ autoAnalysisParams }: ChatWithAIProps) => {
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
          // Track the initial assistant message to avoid re-processing
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

  return (
    <div className="flex flex-col h-full w-full">
      <div className="flex items-center gap-2 p-3 text-[#2463EB]">
        <Bot />
        <span className="font-semibold">Ответ AI ассистента</span>
      </div>
      <div className="flex-1 min-h-0 overflow-hidden">
        <ScrollArea className="h-full w-full p-2">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`p-3 rounded-2xl max-w-[80%] whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-[#F8FAFC] ml-auto text-black w-fit"
                  : "bg-none text-gray-900"
              }`}
            >
              {msg.text}
            </div>
          ))}
          {isAssistantTyping && <TypingIndicator />}
        </ScrollArea>
      </div>
      <div className="flex min-h-0 w-full gap-2 p-2 border-t bg-white">
        <Input
          className="flex-1 min-w-0 active:shadow-0"
          placeholder="Задать вопрос или уточнение..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <Button onClick={sendMessage} disabled={isSending}>
          ➤
        </Button>
      </div>
    </div>
  );
};
