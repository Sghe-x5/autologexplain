import { Bot } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { FC } from "react";

interface UserLogExplanation {
  userId: number;
  period: string | null;
  service: string;
  visits: number;
  sessionDurationSeconds: number;
  sessionDurationReadable: string;
  purchases: {
    count: number;
    totalAmount: number;
  };
  refunds: {
    count: number;
    totalAmount: number;
  };
  summary: string;
}

const mockData: UserLogExplanation = {
  userId: 123,
  period: null,
  service: "userService",
  visits: 1,
  sessionDurationSeconds: 1806,
  sessionDurationReadable: "примерно 30 минут",
  purchases: {
    count: 0,
    totalAmount: 0.0,
  },
  refunds: {
    count: 1,
    totalAmount: 1800.51,
  },
  summary:
    "Пользователь, вероятно, пытался вернуть товар без фактической покупки в рамках этой сессии или возврат относится к более раннему заказу.",
};

const fields: {
  key: keyof typeof mockData;
  label: string;
  render?: (v: any) => string;
}[] = [
  {
    key: "period",
    label: "Рассматриваемый период",
    render: (v) => v ?? "не указан",
  },
  {
    key: "service",
    label: "Сервис",
  },
  {
    key: "visits",
    label: "Количество визитов",
  },
  {
    key: "sessionDurationSeconds",
    label: "Общая продолжительность сессии",
    render: () =>
      `${mockData.sessionDurationSeconds} секунд (${mockData.sessionDurationReadable})`,
  },
  {
    key: "purchases",
    label: "Покупки",
    render: () =>
      mockData.purchases.count === 0
        ? `Пользователь не совершал покупок (${mockData.purchases.totalAmount.toFixed(
            2
          )} продаж)`
        : `${
            mockData.purchases.count
          } покупк(и) на сумму ${mockData.purchases.totalAmount.toFixed(2)}`,
  },
  {
    key: "refunds",
    label: "Возвраты",
    render: () =>
      `${
        mockData.refunds.count
      } возврат на сумму ${mockData.refunds.totalAmount.toFixed(2)}`,
  },
  {
    key: "summary",
    label: "Вывод",
  },
];

const BotAnswer: FC = () => {
  return (
    <div className="space-y-4">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        <Bot className="w-5 h-5" /> Результат анализа
      </h1>

      <Card className="p-4 border-solid border-[#e2e8f0] ring-offset-0 outline-0 bg-[#f1f5f980]">
        {fields.map(({ key, label, render }) => (
          <p key={String(key)} className="text-[16px]">
            {label}: {render ? render(mockData[key]) : String(mockData[key])}
          </p>
        ))}
      </Card>
    </div>
  );
};

export { BotAnswer };
