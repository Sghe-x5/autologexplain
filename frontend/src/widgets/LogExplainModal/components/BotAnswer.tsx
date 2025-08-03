import { Bot } from "lucide-react";
import { Card } from "@/components/ui/card";
import type { FC } from "react";
import { useLogStore } from "../model/store";
import type { UserLogExplanation } from "../model/types";

const BotAnswer: FC = () => {
  const mockData = useLogStore((state) => state.log);

  const fields: {
    key: keyof UserLogExplanation;
    label: string;
    render?: (
      v: any,
      key: keyof UserLogExplanation,
      log: UserLogExplanation
    ) => string;
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
      render: (v, _, log) =>
        `${v} секунд (${log?.sessionDurationReadable ?? "?"})`,
    },
    {
      key: "purchases",
      label: "Покупки",
      render: (v: UserLogExplanation["purchases"]) =>
        v.count === 0
          ? `Пользователь не совершал покупок (${v.totalAmount.toFixed(
              2
            )} продаж)`
          : `${v.count} покупк(и) на сумму ${v.totalAmount.toFixed(2)}`,
    },
    {
      key: "refunds",
      label: "Возвраты",
      render: (v: UserLogExplanation["refunds"]) =>
        `${v.count} возврат на сумму ${v.totalAmount.toFixed(2)}`,
    },
    {
      key: "summary",
      label: "Вывод",
    },
  ];

  return (
    <div className="space-y-4">
      <h1 className="flex items-center gap-2 text-lg font-semibold">
        <Bot className="w-5 h-5" /> Результат анализа
      </h1>

      {mockData ? (
        <Card className="p-4 border-solid border-[#e2e8f0] ring-offset-0 outline-0 bg-[#f1f5f980]">
          {fields.map(({ key, label, render }) => (
            <p key={String(key)} className="text-[16px]">
              {label}:{" "}
              {render
                ? render(mockData[key], key, mockData)
                : String(mockData[key])}
            </p>
          ))}
        </Card>
      ) : (
        <div>Нет результатов анализа</div>
      )}
    </div>
  );
};

export { BotAnswer };
