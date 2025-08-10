import { LogExplainForm } from "../components/Form";
import { Separator } from "@/components/ui/separator";
import { ChatWithAI } from "@/widgets/LogExplainModal/components/ChatWithAI";
import { Bot, X } from "lucide-react";
import { useDispatch } from "react-redux";
import { type AppDispatch } from "@/lib/store";
import { close } from "@/widgets/LogExplainModal/model/showModalSlice";

export const LogExplainUI = () => {
  const dispatch = useDispatch<AppDispatch>();
  return (
    <div className="p-5 absolute top-0 z-50 bg-white">
      <div className="flex justify-between">
        <div className="flex gap-3 items-center">
          <div className="p-4 w-fit bg-[#DBE9FE] rounded-lg">
            <Bot color="#2463EB" />
          </div>
          <div>
            <h1 className="font-[700] text-[#020817] text-[24px]">
              AI Ассистент
            </h1>
            <p className="text-[#64748b] font-[400] text-[16px]">
              Задайте параметры для анализа логов
            </p>
          </div>
        </div>
        <button
          className="p-4 w-fit h-fit bg-none"
          onClick={() => dispatch(close())}
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      <Separator className="my-5" />
      <section>
        <LogExplainForm />
      </section>
      <Separator className="my-8" />
      <ChatWithAI />
    </div>
  );
};
