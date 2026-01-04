import LogExplainUI from "@/widgets/LogExplainModal";
import "./App.css";
import { createPortal } from "react-dom";

import { useDispatch, useSelector } from "react-redux";
import { LogExplainBtn } from "@/widgets/LogExplainModal/components/LogExplainBtn";
import type { AppDispatch, RootState } from "@/lib/store";
import { useEffect, useState } from "react";
import { type FilterData, GetFilters } from "@/api/getFilters";
import { close } from "@/widgets/LogExplainModal/model/showModalSlice";

const FILTERS_KEY = "logExplainFilters";

function App() {
  const modalRoot = document.getElementById("logExplainModal");
  const isShown = useSelector((state: RootState) => state.showModal.isShown);

  const [filters, setFilters] = useState<FilterData[]>([]);
  const [isFiltersLoaded, setFiltersLoaded] = useState(false);
  const dispatch = useDispatch<AppDispatch>();

  useEffect(() => {
    const saved = localStorage.getItem(FILTERS_KEY);

    try {
      if (saved) {
        setFilters(JSON.parse(saved) as FilterData[]);
        setFiltersLoaded(true);
      }
    } catch {
      console.warn("localStorage filters parse error, fallback to API");
    }
    try {
      GetFilters()
        .then((data) => {
          setFilters(data);
          localStorage.setItem(FILTERS_KEY, JSON.stringify(data));
        })
        .catch((err) => console.error(err))
        .finally(() => setFiltersLoaded(true));
    } catch {
      console.error("failed to fetch filters");
    }
  }, []);

  useEffect(() => {
    if (isShown) {
      modalRoot?.classList.remove("translate-x-full", "opacity-0");
      modalRoot?.classList.add("translate-x-0", "opacity-100");
    } else {
      modalRoot?.classList.remove("translate-x-0", "opacity-100");
      modalRoot?.classList.add("translate-x-full", "opacity-0");
    }
  }, [isShown, modalRoot?.classList]);

  return (
    <main data-test-id="app-root">
      <div className="w-full max-w-screen h-full max-h-screen overflow-hidden">
        <img src="/images/AppBG.webp" data-test-id="app-background" />
      </div>

      {modalRoot !== null &&
        isShown &&
        createPortal(
          <>
            <div
              className="flex-1 max-[580px]:hidden inset-0 bg-[#18181B99] backdrop-blur-sm z-40"
              data-test-id="modal-backdrop"
              onClick={() => dispatch(close())}
            ></div>
            <LogExplainUI
              filters={filters}
              isFiltersLoaded={isFiltersLoaded}
              data-test-id="log-explain-ui"
            />
          </>,
          modalRoot
        )}

      <LogExplainBtn data-test-id="log-explain-button" />
    </main>
  );
}

export default App;
