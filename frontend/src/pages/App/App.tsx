import LogExplainUI from "@/widgets/LogExplainModal";
import "./App.css";
import { Separator } from "@/components/ui/separator";
import { BotAnswer } from "@/widgets/LogExplainModal/components/BotAnswer";
import { Bot } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import clsx from "clsx";

function App() {
  const [isModalOpen, setModalOpen] = useState<boolean>(false);

  return (
    <>
      {isModalOpen && (
        <div
          className="fixed inset-0 bg-[#18181B99] backdrop-blur-sm z-40"
          onClick={() => setModalOpen(false)}
        />
      )}

      <div
        className={clsx(
          "fixed top-0 right-0 h-full w-1/2 bg-white shadow-lg z-50 transform transition-transform duration-800",
          isModalOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        <div className="p-5 modal h-full overflow-y-auto relative">
          <button
            onClick={() => setModalOpen(false)}
            className="absolute top-5 right-5 text-[#71717A] hover:text-[#2463EB] transition-colors cursor-pointer"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              width="16"
              height="16"
              viewBox="0 0 32 32"
              fill="currentColor"
            >
              <path d="M17.06 16l7.97 7.97-1.06 1.06L16 17.06l-7.97 7.97-1.06-1.06L14.94 16 6.97 8.03l1.06-1.06L16 14.94l7.97-7.97 1.06 1.06L17.06 16z" />
            </svg>
          </button>

          <div className="flex gap-3 items-center mt-[8px]">
            <div className="p-4 w-fit bg-[#DBE9FE] rounded-lg">
              <Bot color="#2463EB" />
            </div>
            <div>
              <h1 className="font-[700] text-[#020817] text-[24px]">
                AI Ассистент
              </h1>
              <p className="text-[#64748b] font-[400] text-[16px]">
                Задайте параметры для анализа логов
              </p>
            </div>
          </div>

          <Separator className="my-5" />
          <LogExplainUI />
          <Separator className="my-8" />
          <BotAnswer />
        </div>
      </div>

      {!isModalOpen && 
      <Button
        data-test-id="open-modal-button"
        onClick={() => setModalOpen(true)}
        className="inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium fixed bottom-6 right-6 h-16 w-16 rounded-full shadow-xl transition-all duration-300 z-50 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 border-2 border-white/20 hover:scale-110 cursor-pointer"
      >
        <svg
          xmlns="http://www.w3.org/2000/svg"
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          className="lucide lucide-bot h-8 w-8 text-white"
        >
          <path d="M12 8V4H8"></path>
          <rect width="16" height="12" x="4" y="8" rx="2"></rect>
          <path d="M2 14h2"></path>
          <path d="M20 14h2"></path>
          <path d="M15 13v2"></path>
          <path d="M9 13v2"></path>
        </svg>
        <span className="sr-only">Открыть ИИ Ассистента</span>
      </Button>
      }
    </>
  );
}

export default App;
