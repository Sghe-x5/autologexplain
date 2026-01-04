import { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Bot } from "lucide-react";

export const ChatWithAI = () => {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content: `Вот интерпретация действий пользователя с user_001:\n\nРассматриваемый период: не указан\nСервис: не выбран\nКоличество визитов: 1\nОбщая продолжительность сессии: 1806 секунд (примерно 30 минут)\nПокупки: Пользователь не совершал покупок (0.00 продаж)\nВозвраты: 1 возврат на сумму 1800.51\n\nВывод: Пользователь, вероятно, пытался вернуть товар без фактической покупки в рамках этой сессии или возврат относится к более раннему заказу.`,
    },
    {
      role: "user",
      content: "Как исправить эту ошибку?",
    },
    {
      role: "assistant",
      content: "Анализирую...",
    },
  ]);

  const [input, setInput] = useState("");

  const sendMessage = () => {
    if (!input.trim()) return;
    setMessages((prev) => [...prev, { role: "user", content: input }]);
    setInput("");

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "Ответ от ИИ..." },
      ]);
    }, 1000);
  };

  return (
    <div className="w-full h-screen flex flex-col">
      <div className="flex items-center gap-2 p-3 text-[#2463EB]">
        <Bot />
        <span className="font-semibold">Ответ AI ассистента</span>
      </div>
      <div className="flex-1 py-2">
        <div className="space-y-4">
          {messages.map((msg, idx) => (
            <div
              key={idx}
              className={`p-3 rounded-2xl max-w-[80%] whitespace-pre-wrap ${
                msg.role === "user"
                  ? "bg-[#F8FAFC] ml-auto text-black w-fit"
                  : "bg-none text-gray-900"
              }`}
            >
              {msg.content}
            </div>
          ))}
          <div className="w-full h-7"></div>
        </div>
      </div>
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
