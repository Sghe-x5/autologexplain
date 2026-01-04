import DatePicker from "@/features/DatePicker/DatePicker";
import Button from "@/components/ui/button/button";
import {
  Form,
  FormField,
  FormItem,
  FormLabel,
  FormControl,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectGroup,
  SelectItem,
} from "@/components/ui/select";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, useController, type Control } from "react-hook-form";
import { Separator } from "@/components/ui/separator";
import {
  logFormSchema,
  type LogExplanation,
  type UserLogExplanation,
} from "../model/types";
import { useLogStore } from "../model/store";
import { getPeriod } from "@/lib/getPeriod";
import { Sparkles } from "lucide-react";
import { useAutoAnalysisMutation } from "@/api/chatMessagesApi";

import { type FilterData } from "@/api/getFilters";
import { Textarea } from "@/components/ui/textarea";

const mockData: UserLogExplanation = {
  userId: 123,
  period: null,
  service: "userService",
  visits: 1,
  sessionDurationSeconds: 1806,
  sessionDurationReadable: "примерно 30 минут",
  purchases: {
    count: 0,
    totalAmount: 0.0,
  },
  refunds: {
    count: 1,
    totalAmount: 1800.51,
  },
  summary:
    "Пользователь, вероятно, пытался вернуть товар без фактической покупки в рамках этой сессии или возврат относится к более раннему заказу.",
};

const LogExplainForm = ({ filters }: { filters: FilterData[] }) => {
  const form = useForm<LogExplanation>({
    resolver: zodResolver(logFormSchema),
    defaultValues: {
      product: "",
      service: "",
      environment: "",
      startTime: new Date(),
      endTime: new Date(),
      comment: "",
    },
  });

  const setLog = useLogStore((state) => state.setLog);
  const setAnalysisParams = useLogStore((state) => state.setAnalysisParams);
  const [autoAnalysis, { isLoading: isAnalysisLoading }] =
    useAutoAnalysisMutation();

  const onSubmit = async (values: LogExplanation) => {
    try {
      mockData.userId = 123;
      mockData.period = getPeriod({
        startTime: values.startTime,
        endTime: values.endTime,
      });
      setLog(mockData);

      const filters = {
        start_date: values.startTime.toISOString(),
        end_date: values.endTime.toISOString(),
        service: values.service,
      };

      const userNote =
        values.comment && values.comment.trim().length > 0
          ? `Учти: ${values.comment.trim()}`
          : "";

      const prompt = `Проанализируй логи для сервиса ${
        values.service
      } в окружении ${
        values.environment
      } за период с ${values.startTime.toLocaleString()} по ${values.endTime.toLocaleString()}. Предоставь детальный анализ и рекомендации. ${userNote}`;

      const analysisParams = { filters, prompt };
      setAnalysisParams(analysisParams);

      await autoAnalysis();
    } catch (error) {
      console.error("Failed to start analysis:", error);
    }
  };

  const interactiveField =
    "border border-gray-300 rounded-md transition-colors duration-200 " +
    "hover:border-[#2463EB] focus-within:border-[#2463EB] " +
    "focus-within:ring-2 focus-within:ring-[#93C5FD]/40";

  const isFormDisabled = !form.formState.isValid || form.formState.isSubmitting;

  // вместо watch — читаем напрямую через useController внутри каждого поля
  const { field: productField } = useController({
    name: "product",
    control: form.control,
  });
  const productData = filters.find((p) => p.product === productField.value);

  const { field: serviceField } = useController({
    name: "service",
    control: form.control,
  });
  const serviceData = productData?.services.find(
    (s) => s.service === serviceField.value
  );

  const { field: environmentField } = useController({
    name: "environment",
    control: form.control,
  });

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="space-y-6 flex flex-col"
        data-test-id="log-explain-form"
      >
        {/* Продукт */}
        <FormItem data-test-id="product-select">
          <FormLabel>Продукт</FormLabel>
          <Select
            onValueChange={(value) => {
              productField.onChange(value);
              form.setValue("service", "");
              form.setValue("environment", "");
              form.setValue("startTime", new Date());
              form.setValue("endTime", new Date());
            }}
            value={productField.value}
          >
            <FormControl>
              <SelectTrigger
                className={`w-full ${interactiveField} cursor-pointer`}
                data-test-id="product-select-trigger"
              >
                <SelectValue placeholder="Выберите продукт" />
              </SelectTrigger>
            </FormControl>
            <SelectContent data-test-id="product-select-options">
              <SelectGroup>
                {filters.map((p) => (
                  <SelectItem
                    key={p.product}
                    value={p.product}
                    className="cursor-pointer"
                    data-test-id={`product-option-${p.product}`}
                  >
                    {p.product}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          <FormMessage />
        </FormItem>

        {/* Сервис */}
        <FormItem data-test-id="service-select">
          <FormLabel>Сервис</FormLabel>
          <Select
            disabled={!productField.value}
            onValueChange={(value) => {
              serviceField.onChange(value);
              form.setValue("environment", "");
              form.setValue("startTime", new Date());
              form.setValue("endTime", new Date());
            }}
            value={serviceField.value}
          >
            <FormControl>
              <SelectTrigger
                className={`w-full ${interactiveField} disabled:cursor-not-allowed [&:not(:disabled)]:cursor-pointer`}
                data-test-id="service-select-trigger"
              >
                <SelectValue placeholder="Выберите сервис" />
              </SelectTrigger>
            </FormControl>
            <SelectContent data-test-id="service-select-options">
              <SelectGroup>
                {productData?.services.map((s) => (
                  <SelectItem
                    key={s.service}
                    value={s.service}
                    className="cursor-pointer"
                    data-test-id={`service-option-${s.service}`}
                  >
                    {s.service}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          <FormMessage />
        </FormItem>

        {/* Окружение */}
        <FormItem data-test-id="environment-select">
          <FormLabel>Окружение</FormLabel>
          <Select
            disabled={!serviceField.value}
            onValueChange={(value) => {
              environmentField.onChange(value);
              form.setValue("startTime", new Date());
              form.setValue("endTime", new Date());
            }}
            value={environmentField.value}
          >
            <FormControl>
              <SelectTrigger
                className={`w-full ${interactiveField} disabled:cursor-not-allowed [&:not(:disabled)]:cursor-pointer`}
                data-test-id="environment-select-trigger"
              >
                <SelectValue placeholder="Выберите окружение" />
              </SelectTrigger>
            </FormControl>
            <SelectContent data-test-id="environment-select-options">
              <SelectGroup>
                {serviceData?.environments.map((env) => (
                  <SelectItem
                    key={env}
                    value={env}
                    className="cursor-pointer"
                    data-test-id={`environment-option-${env}`}
                  >
                    {env}
                  </SelectItem>
                ))}
              </SelectGroup>
            </SelectContent>
          </Select>
          <FormMessage />
        </FormItem>

        {/* Период */}
        <FormItem data-test-id="period-fields">
          <FormLabel>Период</FormLabel>
          <div className="flex gap-4">
            <FormField
              control={form.control}
              name="startTime"
              render={({ field }) => (
                <FormItem className="flex-1" data-test-id="start-time-picker">
                  <FormControl>
                    <div className={interactiveField}>
                      <div
                        className={
                          !environmentField.value
                            ? "pointer-events-none opacity-50"
                            : ""
                        }
                      >
                        <DatePicker
                          label=""
                          value={field.value}
                          onChange={field.onChange}
                        />
                      </div>
                    </div>
                  </FormControl>
                  <FormMessage />
                  <FormLabel className="text-[#71717A] ml-2">
                    Время начала
                  </FormLabel>
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="endTime"
              render={({ field }) => (
                <FormItem className="flex-1" data-test-id="end-time-picker">
                  <FormControl>
                    <div className={interactiveField}>
                      <div
                        className={
                          !environmentField.value
                            ? "pointer-events-none opacity-50"
                            : ""
                        }
                      >
                        <DatePicker
                          label=""
                          value={field.value}
                          onChange={field.onChange}
                        />
                      </div>
                    </div>
                  </FormControl>
                  <FormMessage />
                  <FormLabel className="text-[#71717A] ml-2">
                    Время окончания
                  </FormLabel>
                </FormItem>
              )}
            />
          </div>
        </FormItem>

        {/* Комментарий */}
        <CommentField control={form.control} disabled={!productField.value} />

        <Separator data-test-id="form-separator" />

        <Button
          type="submit"
          className="bg-[#2463EB] text-[#FAFAFA] hover:bg-[#1C4ED8] hover:border hover:border-[#1C4ED8] cursor-pointer"
          disabled={isFormDisabled || isAnalysisLoading}
          data-test-id="analyze-submit-button"
        >
          <Sparkles />{" "}
          {isAnalysisLoading ? "Анализирую..." : "Анализировать логи"}
        </Button>
      </form>
    </Form>
  );
};

/** Вынесенное поле комментария */
function CommentField({
  control,
  disabled,
}: {
  control: Control<LogExplanation>;
  disabled: boolean;
}) {
  const { field } = useController({ name: "comment", control });
  const charCount = field.value?.length ?? 0;
  const percent = Math.min((charCount / 1000) * 100, 100);
  const counterColor =
    percent >= 100
      ? "text-red-500"
      : percent >= 80
      ? "text-yellow-500"
      : "text-muted-foreground";

  return (
    <FormItem data-test-id="comment-field">
      <FormLabel>Задать вопрос или уточнение AI ассистенту</FormLabel>
      <FormControl>
        <Textarea
          {...field}
          disabled={disabled}
          maxLength={1000}
          placeholder="Например: что означает эта ошибка..."
          className="min-h-[200px] max-h-[300px] resize-y"
          data-test-id="comment-textarea"
        />
      </FormControl>
      <div className="flex items-center justify-between mt-1">
        <span
          className={`text-xs ml-auto ${counterColor}`}
          data-test-id="comment-counter"
        >
          {charCount}/1000
        </span>
      </div>
      <FormMessage />
    </FormItem>
  );
}

export { LogExplainForm };
