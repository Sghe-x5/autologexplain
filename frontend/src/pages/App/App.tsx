import LogExplainUI from "@/widgets/LogExplainModal";
import "./App.css";
import { createPortal } from "react-dom";

import { useSelector } from "react-redux";
import { LogExplainBtn } from "@/widgets/LogExplainModal/components/LogExplainBtn";
import type { RootState } from "@/lib/store";
import { useEffect } from "react";

function App() {
  const modalRoot = document.getElementById("logExplainModal");

  const isShown = useSelector((state: RootState) => state.showModal.isShown);

  useEffect(() => {
    if (isShown) {
      modalRoot?.classList.remove('translate-x-full', 'opacity-0');
      modalRoot?.classList.add('translate-x-0', 'opacity-100');
    } else {
      modalRoot?.classList.remove('translate-x-0', 'opacity-100');
      modalRoot?.classList.add('translate-x-full', 'opacity-0');
    }
  }, [isShown]);

  return (
    <main>
      {isShown &&
      <div
          className="fixed inset-0 bg-[#18181B99] backdrop-blur-sm z-40"
        >
      </div>
      }
      <img src="/images/AppBG.webp" />
      {modalRoot !== null &&
        isShown &&
        createPortal(<LogExplainUI />, modalRoot)}
      <LogExplainBtn />

    </main>
  );
}

export default App;
