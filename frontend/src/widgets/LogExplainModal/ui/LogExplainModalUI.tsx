import { LogExplainForm } from "../components/Form";
import { Separator } from "@/components/ui/separator";
import { ChatWithAI } from "@/widgets/LogExplainModal/components/ChatWithAI";
import { Bot, RotateCcw, X } from "lucide-react";
import { useDispatch } from "react-redux";
import { type AppDispatch } from "@/lib/store";
import { close } from "@/widgets/LogExplainModal/model/showModalSlice";
import { useLogStore } from "../model/store";
import Button from "@/components/ui/button/button";
import { type FilterData, GetFilters } from "@/api/getFilters";
import { useState, useEffect } from "react";

export const LogExplainUI = () => {
  const [filters, setFilters] = useState<FilterData[]>([]);
  const [isFiltersLoaded, setFiltersLoaded] = useState<boolean>(false);
  useEffect(() => {
    GetFilters()
      .then(setFilters)
      .then(() => setFiltersLoaded(true));
  }, []);

  const dispatch = useDispatch<AppDispatch>();
  const hasLog = useLogStore((state) => state.log) !== null;
  const analysisParams = useLogStore((state) => state.analysisParams);

  const resetLog = useLogStore((state) => state.reset);

  const onReset = () => {
    resetLog();
  };

  return (
    <div className="w-full h-full p-5 absolute top-0 z-50 bg-white">
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
              {hasLog
                ? "Результаты анализа логов по заданным параметрам"
                : "Задайте параметры для анализа логов"}
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

      {hasLog && (
        <Button
          type="button"
          className="w-full mt-4 h-11 border"
          variant="ghost"
          onClick={onReset}
        >
          <RotateCcw /> Сбросить и задать новые параметры
        </Button>
      )}

      <Separator className="my-5" />
      {!isFiltersLoaded ? (
        <>
          <span className="loader"></span>
        </>
      ) : (
        <>
          {!hasLog && (
            <section>
              <LogExplainForm filters={filters} />
            </section>
          )}
          {hasLog && (
            <ChatWithAI autoAnalysisParams={analysisParams || undefined} />
          )}
        </>
      )}
    </div>
  );
};
