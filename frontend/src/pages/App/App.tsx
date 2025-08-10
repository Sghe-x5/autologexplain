import LogExplainUI from "@/widgets/LogExplainModal";
import "./App.css";
import { createPortal } from "react-dom";

import { useSelector } from "react-redux";
import { LogExplainBtn } from "@/widgets/LogExplainModal/components/LogExplainBtn";
import type { RootState } from "@/lib/store";

function App() {
  const modalRoot = document.getElementById("logExplainModal");

  const isShown = useSelector((state: RootState) => state.showModal.isShown);

  return (
    <main>
      <img src="/images/AppBG.webp" />
      {modalRoot !== null &&
        isShown &&
        createPortal(<LogExplainUI />, modalRoot)}
      <LogExplainBtn />
    </main>
  );
}

export default App;
