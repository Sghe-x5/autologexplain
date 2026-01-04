import { FormInput as Input } from "./FormInput";
import DatePicker from "@/features/DatePicker/DatePicker";
import { Button } from "@/components/ui/button";
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
import { useForm } from "react-hook-form";
import { Separator } from "@/components/ui/separator";
import {
  logFormSchema,
  type LogExplanation,
  type UserLogExplanation,
} from "../model/types";
import { useLogStore } from "../model/store";
import { getPeriod } from "@/lib/getPeriod";
import { Sparkles } from "lucide-react";

import { FILTERS } from "@/mocks/filter.mock";

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

const LogExplainForm = () => {
  const form = useForm<LogExplanation>({
    resolver: zodResolver(logFormSchema),
    defaultValues: {
      product: "",
      service: "",
      environment: "",
      startTime: new Date(),
      endTime: new Date(),
    },
  });

  const setLog = useLogStore((state) => state.setLog);

  const watchProduct = form.watch("product");
  const watchService = form.watch("service");
  const watchEnvironment = form.watch("environment");

  const onSubmit = (values: LogExplanation) => {
    mockData.userId = 123;
    mockData.period = getPeriod({
      startTime: values.startTime,
      endTime: values.endTime,
    });
    setLog(mockData);
  };

  const interactiveField =
    "border border-gray-300 rounded-md transition-colors duration-200 " +
    "hover:border-[#2463EB] focus-within:border-[#2463EB] " +
    "focus-within:ring-2 focus-within:ring-[#93C5FD]/40";

  const isFormDisabled =
    !form.formState.isValid || form.formState.isSubmitting;

  const productData = FILTERS.find((p) => p.product === watchProduct);
  const serviceData = productData?.services.find(
    (s) => s.service === watchService
  );

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="space-y-6 flex flex-col"
      >
        <FormField
          control={form.control}
          name="product"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Продукт</FormLabel>
              <Select
                onValueChange={(value) => {
                  field.onChange(value);
                  form.setValue("service", "");
                  form.setValue("environment", "");
                  form.setValue("startTime", new Date());
                  form.setValue("endTime", new Date());
                }}
                value={field.value}
              >
                <FormControl>
                  <SelectTrigger
                    className={`w-full ${interactiveField} cursor-pointer`}
                  >
                    <SelectValue placeholder="Выберите продукт" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectGroup>
                    {FILTERS.map((p) => (
                      <SelectItem key={p.product} value={p.product} className="cursor-pointer">
                        {p.product}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="service"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Сервис</FormLabel>
              <Select
                disabled={!watchProduct}
                onValueChange={(value) => {
                  field.onChange(value);
                  form.setValue("environment", "");
                  form.setValue("startTime", new Date());
                  form.setValue("endTime", new Date());
                }}
                value={field.value}
              >
                <FormControl>
                  <SelectTrigger
                    className={`w-full ${interactiveField} disabled:cursor-not-allowed [&:not(:disabled)]:cursor-pointer`}
                  >
                    <SelectValue placeholder="Выберите сервис" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectGroup>
                    {productData?.services.map((s) => (
                      <SelectItem key={s.service} value={s.service} className="cursor-pointer">
                        {s.service}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="environment"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Окружение</FormLabel>
              <Select
                disabled={!watchService}
                onValueChange={(value) => {
                  field.onChange(value);
                  form.setValue("startTime", new Date());
                  form.setValue("endTime", new Date());
                }}
                value={field.value}
              >
                <FormControl>
                  <SelectTrigger
                    className={`w-full ${interactiveField} disabled:cursor-not-allowed [&:not(:disabled)]:cursor-pointer`}
                  >
                    <SelectValue placeholder="Выберите окружение" />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectGroup>
                    {serviceData?.environments.map((env) => (
                      <SelectItem key={env} value={env} className="cursor-pointer">
                        {env}
                      </SelectItem>
                    ))}
                  </SelectGroup>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormItem>
          <FormLabel>Период</FormLabel>
          <div className="flex gap-4">
            <FormField
              control={form.control}
              name="startTime"
              render={({ field }) => (
                <FormItem className="flex-1">
                  <FormControl>
                    <div className={interactiveField}>
                      <div
                        className={
                          !watchEnvironment
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
                <FormItem className="flex-1">
                  <FormControl>
                    <div className={interactiveField}>
                      <div
                        className={
                          !watchEnvironment
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

        <Separator />

        <Button
          type="submit"
          className=" bg-[#93C5FD] text-[#FAFAFA] hover:bg-[#93C5FD] hover:border hover:border-[#2463EB]"
          disabled={isFormDisabled}
        >
          <Sparkles /> Анализировать логи
        </Button>
      </form>
    </Form>
  );
};

export { LogExplainForm };

