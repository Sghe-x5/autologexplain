import LogExplainUI from "@/widgets/LogExplainModal";
import "./App.css";
import { createPortal } from "react-dom";

import { useSelector } from "react-redux";
import { LogExplainBtn } from "@/widgets/LogExplainModal/components/LogExplainBtn";
import type { RootState } from "@/lib/store";
import { useEffect, useState } from "react";
import { type FilterData, GetFilters } from "@/api/getFilters";

const FILTERS_KEY = "logExplainFilters";

function App() {
  const modalRoot = document.getElementById("logExplainModal");
  const isShown = useSelector((state: RootState) => state.showModal.isShown);

  const [filters, setFilters] = useState<FilterData[]>([]);
  const [isFiltersLoaded, setFiltersLoaded] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem(FILTERS_KEY);

    if (saved) {
      try {
        setFilters(JSON.parse(saved) as FilterData[]);
        setFiltersLoaded(true);
      } catch {
        console.warn("localStorage filters parse error, fallback to API");
      }
    }

    if (!saved) {
      GetFilters()
        .then((data) => {
          setFilters(data);
          localStorage.setItem(FILTERS_KEY, JSON.stringify(data));
        })
        .finally(() => setFiltersLoaded(true));
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
    <main>
      {isShown && (
        <div className="fixed inset-0 bg-[#18181B99] backdrop-blur-sm z-40"></div>
      )}

      <img src="/images/AppBG.webp" />

      {modalRoot !== null &&
        isShown &&
        createPortal(
          <LogExplainUI
            filters={filters}
            isFiltersLoaded={isFiltersLoaded}
          />,
          modalRoot
        )}

      <LogExplainBtn />
    </main>
  );
}

export default App;
