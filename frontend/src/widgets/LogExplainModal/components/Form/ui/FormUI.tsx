import Button from "@/components/ui/button/button";
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Separator } from "@/components/ui/separator";
import { Textarea } from "@/components/ui/textarea";
import DatePicker from "@/features/DatePicker/DatePicker";
import type { UseFormReturn, Control } from "react-hook-form";
import type { FilterData } from "@/api/getFilters";
import type { LogExplanation } from "../../../model/types";

export interface FormUIProps {
  form: UseFormReturn<LogExplanation>;
  filters: FilterData[];
  productData?: FilterData;
  serviceData?: { service: string; environments: string[] };
  isFormDisabled: boolean;
  isAnalysisLoading: boolean;
  onProductChange: (value: string) => void;
  onServiceChange: (value: string) => void;
  onEnvironmentChange: (value: string) => void;
  onSubmit: (values: LogExplanation) => void | Promise<void>;
}

export function FormUI({
  form,
  filters,
  productData,
  serviceData,
  isFormDisabled,
  isAnalysisLoading,
  onProductChange,
  onServiceChange,
  onEnvironmentChange,
  onSubmit,
}: FormUIProps) {
  const interactiveField =
    "border border-gray-300 rounded-md transition-colors duration-200 " +
    "hover:border-[#2463EB] focus-within:border-[#2463EB] " +
    "focus-within:ring-2 focus-within:ring-[#93C5FD]/40";

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
            onValueChange={onProductChange}
            value={form.getValues("product")}
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
            disabled={!form.getValues("product")}
            onValueChange={onServiceChange}
            value={form.getValues("service")}
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
            disabled={!form.getValues("service")}
            onValueChange={onEnvironmentChange}
            value={form.getValues("environment")}
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
                          !form.getValues("environment")
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
                          !form.getValues("environment")
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
        <CommentField
          control={form.control}
          disabled={!form.getValues("product")}
        />

        <Separator data-test-id="form-separator" />

        <Button
          type="submit"
          className="bg-[#2463EB] text-[#FAFAFA] hover:bg-[#1C4ED8] hover:border hover:border-[#1C4ED8] cursor-pointer"
          disabled={isFormDisabled}
          data-test-id="analyze-submit-button"
        >
          {isAnalysisLoading ? "Анализирую..." : "Анализировать логи"}
        </Button>
      </form>
    </Form>
  );
}

function CommentField({
  control,
  disabled,
}: {
  control: Control<LogExplanation>;
  disabled: boolean;
}) {
  const { field } = (Form as any).useController
    ? (Form as any).useController({ name: "comment", control })
    : { field: { value: "", onChange: () => {} } };

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
