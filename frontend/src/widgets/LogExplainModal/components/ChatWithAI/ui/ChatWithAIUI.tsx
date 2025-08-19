import { Input } from "@/components/ui/input";
import Button from "@/components/ui/button/button";
import { Bot } from "lucide-react";
import { ScrollArea } from "@/components/ui/scroll-area";
import type { ChatItem } from "@/lib/chat.schemas";

const TypingIndicator = () => (
  <div className="flex gap-1 items-center text-gray-500 px-3 py-2">
    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]" />
    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]" />
    <span className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
  </div>
);

export interface ChatWithAIUIProps {
  messages: ChatItem[];
  input: string;
  isAssistantTyping: boolean;
  isSending: boolean;
  onInputChange: (value: string) => void;
  onSend: () => void;
}

export function ChatWithAIUI({
  messages,
  input,
  isAssistantTyping,
  isSending,
  onInputChange,
  onSend,
}: ChatWithAIUIProps) {
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
          onChange={(e) => onInputChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSend()}
        />
        <Button onClick={onSend} disabled={isSending}>
          ➤
        </Button>
      </div>
    </div>
  );
}
