import LogExplainUI from "@/widgets/LogExplainModal";
import "./App.css";
import { Separator } from "@/components/ui/separator";
import { BotAnswer } from "@/widgets/LogExplainModal/components/BotAnswer";
import { Bot } from "lucide-react";

function App() {
  return (
    <div className="p-5">
      <div className="flex gap-3">
        <div className="p-2.5 w-fit h-fit bg-gray-200 rounded-lg">
          <Bot />
        </div>
        <div>
          <h1 className="font-[600] text-[#020817] text-[18px]">
            ИИ Ассистент
          </h1>
          <p className="text-[#64748b] text-[14px]">
            Настройте параметры для интеллектуального анализа логов
          </p>
        </div>
      </div>
      <Separator className="mt-5 mb-12" />
      <LogExplainUI />
      <Separator className="my-8" />
      <BotAnswer />
    </div>
  );
}

export default App;
