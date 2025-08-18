import "./App.css";
import { createPortal } from "react-dom";

import { LogExplainBtn } from "@/widgets/LogExplainModal/components/LogExplainBtn";
import { useLogExplainModal } from "@/widgets/LogExplainModal/model/useLogExplainModal";
import LogExplainModal from "@/widgets/LogExplainModal";

function App() {
  const modalRoot = document.getElementById("logExplainModal");
  const { isShown, onBackdropClick } = useLogExplainModal();

  return (
    <main data-test-id="app-root">
      <div className="w-full max-w-screen h-full max-h-screen overflow-hidden">
        <img
          src="/images/AppBG.webp"
          loading="lazy"
          decoding="async"
          alt=""
          data-test-id="app-background"
        />
      </div>

      {modalRoot !== null &&
        isShown &&
        createPortal(
          <>
            <div
              className="flex-1 max-[580px]:hidden inset-0 bg-[#18181B99] z-40"
              data-test-id="modal-backdrop"
              onClick={onBackdropClick}
            ></div>
            <LogExplainModal />
          </>,
          modalRoot
        )}

      <LogExplainBtn data-test-id="log-explain-button" />
    </main>
  );
}

export default App;
