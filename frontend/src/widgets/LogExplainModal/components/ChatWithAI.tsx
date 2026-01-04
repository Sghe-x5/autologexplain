import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Bot } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";

import { useEffect, useMemo, useState } from "react";
import {
  useNewChatMutation,
  useStreamChatQuery,
  useChatTurnMutation,
} from "../model/WebSocket/chat.api";
import { WS_BASE } from "../model/WebSocket/consts";

export const ChatWithAI = () => {
  const [messages, setMessages] = useState<
    { id: string; role: "user" | "assistant"; text: string }[]
  >([]);

  const [input, setInput] = useState("");

  const [newChat] = useNewChatMutation();
  const [chatTurn] = useChatTurnMutation();

  const [chat, setChat] = useState<{ chatId: string; token: string } | null>(
    null
  );

  useEffect(() => {
    (async () => {
      const res = await newChat().unwrap();
      setChat({ chatId: res.chat_id, token: res.token });
    })();
  }, [newChat]);

  const streamParams = useMemo(
    () =>
      chat ? { chatId: chat.chatId, token: chat.token, wsUrl: WS_BASE } : null,
    [chat]
  );

  const { data } = useStreamChatQuery(streamParams!, { skip: !chat });

  useEffect(() => {
    if (data?.items?.length) {
      setMessages((prev) => {
        // Добавляем только новые сообщения, которых еще нет в prev по id
        const existingIds = new Set(prev.map((m) => m.id)); // выделяй id
        const newMessages = data.items
          .filter((m) => !existingIds.has(m.id))
          .map((m) => ({
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
      { id: crypto.randomUUID(), role: "user", text: input.trim() },
    ]);
  };

  return (
    <div className="w-full max-h-full h-full flex flex-col">
      <div className="flex items-center gap-2 p-3 text-[#2463EB]">
        <Bot />
        <span className="font-semibold">Ответ AI ассистента</span>
      </div>
      <ScrollArea className="h-full py-2 px-2">
        {messages.length > 0 &&
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-2xl max-w-[80%] whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-[#F8FAFC] ml-auto text-black w-fit"
                  : "bg-none text-gray-900"
              }`}
            >
              {msg.text}
            </div>
          ))}
      </ScrollArea>
      <div className="flex gap-2 p-2 border-t bg-white sticky bottom-0">
        <Input
          placeholder="Задать вопрос или уточнение..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && sendMessage()}
        />
        <Button onClick={sendMessage} disabled={false}>
          ➤
        </Button>
      </div>
    </div>
  );
};
