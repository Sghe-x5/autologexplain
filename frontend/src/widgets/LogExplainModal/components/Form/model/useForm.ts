import { zodResolver } from "@hookform/resolvers/zod";
import { useMemo } from "react";
import { useForm, useWatch } from "react-hook-form";
import { useDispatch } from "react-redux";
import type { AppDispatch } from "@/lib/store";
import { startAnalysis } from "../../../model/logExplainSlice";
import { useAutoAnalysisMutation } from "@/api/chatMessagesApi";
import type { FilterData } from "@/api/getFilters";
import { logFormSchema, type LogExplanation } from "../../../model/types";

export function useFormLogic(filters: FilterData[]) {
  const form = useForm<LogExplanation>({
    resolver: zodResolver(logFormSchema),
    mode: "onBlur", // ↓ чтобы не пересчитывать валидность на каждый символ
    defaultValues: {
      product: "",
      service: "",
      environment: "",
      startTime: new Date(Date.now() - 24 * 60 * 60 * 1000),
      endTime: new Date(),
      comment: "",
    },
  });

  const dispatch = useDispatch<AppDispatch>();
  const [autoAnalysis, { isLoading: isAnalysisLoading }] =
    useAutoAnalysisMutation();

  // более "дешёвый" watch
  const product = useWatch({ control: form.control, name: "product" });
  const service = useWatch({ control: form.control, name: "service" });

  // строим словарь фильтров один раз
  const filtersByProduct = useMemo(
    () => new Map(filters.map((f) => [f.product, f])),
    [filters]
  );

  const productData = filtersByProduct.get(product);
  const serviceData = useMemo(
    () => productData?.services.find((s) => s.service === service),
    [productData, service]
  );

  const isFormDisabled =
    !form.formState.isValid || form.formState.isSubmitting || isAnalysisLoading;

  const onProductChange = (value: string) => {
    form.setValue("product", value, {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: false,
    });
    form.setValue("service", "", {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: false,
    });
    form.setValue("environment", "", {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: false,
    });
  };

  const onServiceChange = (value: string) => {
    form.setValue("service", value, {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: false,
    });
    form.setValue("environment", "", {
      shouldDirty: true,
      shouldTouch: true,
      shouldValidate: false,
    });
  };

  const onEnvironmentChange = (value: string) => {
    form.setValue("environment", value, { shouldValidate: true });
  };

  const onSubmit = async (values: LogExplanation) => {
    try {
      const payload = {
        start_date: values.startTime.toISOString(),
        end_date: values.endTime.toISOString(),
        product: values.product,
        service: values.service,
        environment: values.environment,
      };
      const prompt = "Найди ошибку и объясни из-за чего она возникла";
      dispatch(startAnalysis({ filters: payload, prompt }));
      await autoAnalysis();
    } catch (error) {
      console.error("Failed to start analysis:", error);
    }
  };

  return {
    form,
    productData,
    serviceData,
    isAnalysisLoading,
    isFormDisabled,
    onProductChange,
    onServiceChange,
    onEnvironmentChange,
    onSubmit,
  };
}
