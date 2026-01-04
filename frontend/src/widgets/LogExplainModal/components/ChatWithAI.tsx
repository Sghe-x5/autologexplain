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
import { useLogStore } from "../model/store";

interface ChatWithAIProps {
  autoAnalysisParams?: {
    filters: { start_date: string; end_date: string; service: string };
    prompt: string;
  };
}

export const ChatWithAI = ({ autoAnalysisParams }: ChatWithAIProps) => {
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [input, setInput] = useState("");
  const [newChat] = useNewChatMutation();
  const [chatTurn] = useChatTurnMutation();
  const [autoAnalysis] = useAutoAnalysisMutation();
  const [isInitializing, setIsInitializing] = useState(false);
  const clearAnalysisParams = useLogStore((state) => state.clearAnalysisParams);

  const [chat, setChat] = useState<{ chatId: string; token: string } | null>(
    null
  );

  const initializationRef = useRef(false);

  // Очистка WebSocket соединений при размонтировании
  useEffect(() => {
    return () => {
      if (chat) {
        const ws = wsRegistry.get(chat.chatId);
        if (ws) {
          console.log("Cleaning up WebSocket connection on unmount");
          ws.close();
          wsRegistry.del(chat.chatId);
        }
      }
    };
  }, [chat]);

  // Сброс состояния при изменении autoAnalysisParams
  useEffect(() => {
    if (autoAnalysisParams === undefined) {
      setMessages([]);
      setInput("");
      initializationRef.current = false;
      setIsInitializing(false);
    }
  }, [autoAnalysisParams]);

  // Автоматический запуск анализа при получении параметров
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
          console.log("Starting auto analysis...");
          const result = await autoAnalysis().unwrap();
          setChat({ chatId: result.chatId, token: result.token });

          setMessages([
            {
              id: crypto.randomUUID(),
              role: "assistant",
              text: "Начинаю анализ логов...",
            } as ChatItem,
          ]);
        } catch (error) {
          console.error("Failed to start auto analysis:", error);
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
          console.log("Creating new chat...");
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
      console.log("WebSocket connected, sending analysis request...");

      const ws = wsRegistry.get(chat.chatId);
      if (ws && ws.readyState === WebSocket.OPEN) {
        const message = {
          type: "analysis_start",
          request_id: crypto.randomUUID(),
          filters: autoAnalysisParams.filters,
          prompt: autoAnalysisParams.prompt,
        };

        console.log("Sending analysis request:", message);
        ws.send(JSON.stringify(message));

        clearAnalysisParams();
      }
    }
  }, [chat, autoAnalysisParams, data?.connected]);

  useEffect(() => {
    if (data?.items?.length) {
      setMessages((prev) => {
        const existingIds = new Set(prev.map((m) => m.id));
        const newMessages = data.items
          .filter((m: ChatItem) => !existingIds.has(m.id))
          .map((m: ChatItem) => ({
            ...m,
            text: m.text
              .replace(/^```json\n/, "")
              .replace(/\n```$/, "")
              .replace(/Запрос: .*/, ""),
          }));

        return [...prev, ...newMessages];
      });
    }
  }, [data]);

  const sendMessage = async () => {
    if (!chat || !input.trim()) return;
    await chatTurn({
      chatId: chat.chatId,
      content: input.trim(),
    });
    setInput("");
    setMessages([
      ...messages,
      { id: crypto.randomUUID(), role: "user", text: input.trim() } as ChatItem,
    ]);
  };

  return (
    <div
      className="w-full max-h-full h-full flex flex-col"
      data-test-id="chat-with-ai"
    >
      <div
        className="flex items-center gap-2 p-3 text-[#2463EB]"
        data-test-id="chat-header"
      >
        <Bot />
        <span className="font-semibold">Ответ AI ассистента</span>
      </div>
      <ScrollArea
        className="h-full py-2 px-2"
        data-test-id="chat-messages-scroll"
      >
        {messages.length > 0 &&
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-2xl max-w-[80%] whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-[#F8FAFC] ml-auto text-black w-fit"
                  : "bg-none text-gray-900"
              }`}
              data-test-id={`chat-message-${msg.role}`}
            >
              {msg.text}
            </div>
          ))}
      </ScrollArea>
      <div
        className="flex gap-2 p-2 border-t bg-white sticky bottom-0"
        data-test-id="chat-input-wrapper"
      >
        <Input
          placeholder="Задать вопрос или уточнение..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
          data-test-id="chat-input"
        />
        <Button
          onClick={sendMessage}
          disabled={false}
          data-test-id="chat-send-button"
        >
          ➤
        </Button>
      </div>
    </div>
  );
};
