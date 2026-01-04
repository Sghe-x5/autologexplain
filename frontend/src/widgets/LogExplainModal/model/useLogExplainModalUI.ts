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

  const onClose = () => dispatch(close());
  const onReset = () => dispatch(resetAnalysis());

  return { isAnalysisActive, analysisParams, onClose, onReset } as const;
}
