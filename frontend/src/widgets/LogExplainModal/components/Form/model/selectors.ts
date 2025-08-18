import type { FilterData } from "@/api/getFilters";
import type { FormState } from "react-hook-form";
import type { LogExplanation } from "../../../model/types";

export const selectProductOptions = (filters: FilterData[]) =>
  filters.map((f) => ({ value: f.product, label: f.product }));

export const selectServiceOptions = (product?: FilterData) =>
  (product?.services ?? []).map((s) => ({
    value: s.service,
    label: s.service,
  }));

export const selectEnvironmentOptions = (service?: {
  service: string;
  environments: string[];
}) => (service?.environments ?? []).map((e) => ({ value: e, label: e }));

export const selectCanSubmit = (formState: FormState<LogExplanation>) =>
  formState.isValid && !formState.isSubmitting;
