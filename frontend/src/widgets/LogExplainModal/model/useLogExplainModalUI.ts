import { useDispatch, useSelector } from "react-redux";
import type { AppDispatch, RootState } from "@/lib/store";
import { close } from "./showModalSlice";
import { resetAnalysis } from "./logExplainSlice";

export function useLogExplainModalUI() {
  const dispatch = useDispatch<AppDispatch>();

  const isAnalysisActive = useSelector(
    (state: RootState) => state.logExplain.isAnalysisActive
  );
  const analysisParams = useSelector(
    (state: RootState) => state.logExplain.analysisParams
  );

  const LS_MESSAGES_KEY = "chat_messages";
  const COOKIE_CHAT_KEY = "chat_session";
  const deleteCookie = (name: string) => {
    try {
      document.cookie = `${name}=; Max-Age=0; path=/`;
    } catch {
      // ignore
    }
  };

  const onClose = () => dispatch(close());
  const onReset = () => {
    try {
      localStorage.removeItem(LS_MESSAGES_KEY);
    } catch {
      // ignore
    }
    deleteCookie(COOKIE_CHAT_KEY);
    dispatch(resetAnalysis());
  };

  return { isAnalysisActive, analysisParams, onClose, onReset } as const;
}
