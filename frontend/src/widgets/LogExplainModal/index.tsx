import { LogExplainUI } from "./ui/LogExplainModalUI";
import { useLogExplainModal } from "./model/useLogExplainModal";
import { useLogExplainModalUI } from "./model/useLogExplainModalUI";

export default function LogExplainModal() {
  const { filters, isFiltersLoaded } = useLogExplainModal();
  const { isAnalysisActive, analysisParams, onClose, onReset } =
    useLogExplainModalUI();

  return (
    <LogExplainUI
      filters={filters}
      isFiltersLoaded={isFiltersLoaded}
      isAnalysisActive={isAnalysisActive}
      analysisParams={analysisParams}
      onClose={onClose}
      onReset={onReset}
    />
  );
}
