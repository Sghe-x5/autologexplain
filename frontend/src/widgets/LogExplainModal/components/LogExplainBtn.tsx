import Button from "@/components/ui/button/button";
import { useDispatch, useSelector } from "react-redux";
import { type AppDispatch, type RootState } from "@/lib/store";
import { open } from "@/widgets/LogExplainModal/model/showModalSlice";

export const LogExplainBtn = () => {
  const isShown = useSelector((state: RootState) => state.showModal.isShown);
  const dispatch = useDispatch<AppDispatch>();
  return (
    <>
      {!isShown && (
        <Button
          data-test-id="open-modal-button"
          onClick={() => dispatch(open())}
          className="inline-flex items-center justify-center gap-2 whitespace-nowrap text-sm font-medium ring-offset-background focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 [&amp;_svg]:pointer-events-none [&amp;_svg]:size-4 [&amp;_svg]:shrink-0 bg-primary text-primary-foreground hover:bg-primary/90 fixed bottom-6 right-6 h-16 w-16 rounded-full shadow-xl hover:shadow-2xl transition-all duration-300 z-40 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 border-2 border-white/20 hover:scale-110 cursor-pointer"
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
      )}
    </>
  );
};
