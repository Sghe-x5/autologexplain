import type { FilterData } from "@/api/getFilters";
import { useFormLogic } from "./model/useForm";
import { FormUI } from "./ui/FormUI";

export function LogExplainForm({ filters }: { filters: FilterData[] }) {
  const logic = useFormLogic(filters);

  return (
    <FormUI
      form={logic.form}
      filters={filters}
      productData={logic.productData}
      serviceData={logic.serviceData}
      isFormDisabled={logic.isFormDisabled}
      isAnalysisLoading={logic.isAnalysisLoading}
      onProductChange={logic.onProductChange}
      onServiceChange={logic.onServiceChange}
      onEnvironmentChange={logic.onEnvironmentChange}
      onSubmit={logic.onSubmit}
    />
  );
}
