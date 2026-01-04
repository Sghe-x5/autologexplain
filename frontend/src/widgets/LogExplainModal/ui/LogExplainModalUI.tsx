import { LogExplainForm } from "../components/Form";
import { Separator } from "@/components/ui/separator";
import { ChatWithAI } from "@/widgets/LogExplainModal/components/ChatWithAI";
import { Bot, RotateCcw, X } from "lucide-react";
import { useDispatch } from "react-redux";
import { type AppDispatch } from "@/lib/store";
import { close } from "@/widgets/LogExplainModal/model/showModalSlice";
import { useLogStore } from "../model/store";
import Button from "@/components/ui/button/button";
import { type FilterData } from "@/api/getFilters";

export const LogExplainUI = ({
  filters,
  isFiltersLoaded,
}: {
  filters: FilterData[];
  isFiltersLoaded: boolean;
}) => {
  const dispatch = useDispatch<AppDispatch>();
  const hasLog = useLogStore((state) => state.log) !== null;
  const analysisParams = useLogStore((state) => state.analysisParams);

  const resetLog = useLogStore((state) => state.reset);

  const onReset = () => {
    resetLog();
  };

  return (
    <div
      className="w-full h-full p-5 absolute top-0 z-50 bg-white"
      data-test-id="log-explain-modal"
    >
      <div className="flex justify-between" data-test-id="log-explain-header">
        <div className="flex gap-3 items-center" data-test-id="header-left">
          <div
            className="p-4 w-fit bg-[#DBE9FE] rounded-lg"
            data-test-id="assistant-icon"
          >
            <Bot color="#2463EB" />
          </div>
          <div>
            <h1
              className="font-[700] text-[#020817] text-[24px]"
              data-test-id="assistant-title"
            >
              AI Ассистент
            </h1>
            <p
              className="text-[#64748b] font-[400] text-[16px]"
              data-test-id="assistant-description"
            >
              {hasLog
                ? "Результаты анализа логов по заданным параметрам"
                : "Задайте параметры для анализа логов"}
            </p>
          </div>
        </div>
        <button
          className="p-4 w-fit h-fit bg-none"
          onClick={() => dispatch(close())}
          data-test-id="close-modal-button"
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
          data-test-id="reset-log-button"
        >
          <RotateCcw /> Сбросить и задать новые параметры
        </Button>
      )}

      <Separator className="my-5" data-test-id="separator" />
      {!isFiltersLoaded ? (
        <>
          <span className="loader" data-test-id="filters-loader"></span>
        </>
      ) : (
        <>
          {!hasLog && (
            <section data-test-id="log-explain-form-section">
              <LogExplainForm filters={filters} />
            </section>
          )}
          {hasLog && (
            <div
              className="h-full max-h-full"
              data-test-id="chat-with-ai-section"
            >
              <ChatWithAI autoAnalysisParams={analysisParams || undefined} />
            </div>
          )}
        </>
      )}
    </div>
  );
};
