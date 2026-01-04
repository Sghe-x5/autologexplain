import { useCallback, useEffect, useState } from "react";
import { useDispatch, useSelector } from "react-redux";

import type { AppDispatch, RootState } from "@/lib/store";
import { GetFilters, type FilterData } from "@/api/getFilters";
import { close } from "./showModalSlice";

const FILTERS_KEY = "logExplainFilters";

export function useLogExplainModal() {
  const dispatch = useDispatch<AppDispatch>();
  const isShown = useSelector((state: RootState) => state.showModal.isShown);

  const [filters, setFilters] = useState<FilterData[]>([]);
  const [isFiltersLoaded, setFiltersLoaded] = useState(false);

  // Load filters from localStorage and then refresh from API
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

  // Animate modal root visibility via CSS classes
  useEffect(() => {
    const modalRoot = document.getElementById("logExplainModal");
    const classList = modalRoot?.classList;
    if (!classList) return;

    if (isShown) {
      classList.remove("translate-x-full", "opacity-0");
      classList.add("translate-x-0", "opacity-100");
    } else {
      classList.remove("translate-x-0", "opacity-100");
      classList.add("translate-x-full", "opacity-0");
    }
  }, [isShown]);

  const onBackdropClick = useCallback(() => {
    dispatch(close());
  }, [dispatch]);

  return { filters, isFiltersLoaded, isShown, onBackdropClick } as const;
}


