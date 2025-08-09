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
      service: "",
      userID: "",
      startTime: new Date(),
      endTime: new Date(),
    },
  });

  const setLog = useLogStore((state) => state.setLog);
  // const resetLog = useLogStore((state) => state.reset);

  const onSubmit = (values: LogExplanation) => {
    mockData.userId = Number(values.userID);
    mockData.period = getPeriod({
      startTime: values.startTime,
      endTime: values.endTime,
    });

    setLog(mockData);
  };

  // const onReset = () => {
  //   form.reset();
  //   resetLog();
  // };
  const interactiveField =
    "border border-gray-300 rounded-md transition-colors duration-200 " +
    "hover:border-[#2463EB] focus-within:border-[#2463EB] " +
    "focus-within:ring-2 focus-within:ring-[#93C5FD]/40";

  const isFormFiled = !form.formState.isValid || form.formState.isSubmitting;

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="space-y-6 flex flex-col"
      >
        <FormField
          control={form.control}
          name="service"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Сервис</FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger
                    className={`w-full ${interactiveField}`}
                    data-test-id="analised-service-select"
                  >
                    <SelectValue
                      placeholder="Выберите сервис для анализа"
                      data-test-id="selected-service-span"
                    />
                  </SelectTrigger>
                </FormControl>
                <SelectContent>
                  <SelectGroup>
                    <SelectItem value="catService">catService</SelectItem>
                    <SelectItem value="paymentService">
                      paymentService
                    </SelectItem>
                    <SelectItem value="userService">userService</SelectItem>
                    <SelectItem value="orderService">orderService</SelectItem>
                    <SelectItem value="inventoryService">
                      inventoryService
                    </SelectItem>
                    <SelectItem value="notificationService">
                      notificationService
                    </SelectItem>
                  </SelectGroup>
                </SelectContent>
              </Select>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormField
          control={form.control}
          name="userID"
          render={({ field }) => (
            <FormItem>
              <FormLabel>ID пользователя</FormLabel>
              <FormControl data-test-id="identifier-input">
                <Input
                  placeholder="Введите userId, sessionId или идентификатор"
                  {...field}
                  className={interactiveField}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <FormItem>
          <FormLabel>Укажите период для анализа</FormLabel>
          <div className="flex gap-4">
            <FormField
              control={form.control}
              name="startTime"
              render={({ field }) => (
                <FormItem className="flex-1">
                  <FormControl>
                    <div className={interactiveField}>
                      <DatePicker
                        label=""
                        value={field.value}
                        onChange={field.onChange}
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                  <FormLabel className="text-[#71717A] ml-2 font-[sans-serif]">Время начала</FormLabel>
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
                      <DatePicker
                        label=""
                        value={field.value}
                        onChange={field.onChange}
                      />
                    </div>
                  </FormControl>
                  <FormMessage />
                  <FormLabel className="text-[#71717A] ml-2 font-[sans-serif]">Время окончания</FormLabel>
                </FormItem>
              )}
            />
          </div>
        </FormItem>

        <Separator />

        <div className="flex gap-2">
          <Button
            data-test-id="analyse-logs-button"
            type="submit"
            className="flex-[11] bg-[#93C5FD] text-[#FAFAFA] hover:bg-[#93C5FD] hover:border hover:border-[#2463EB]"
            disabled={isFormFiled}
          >
            <Sparkles /> Анализировать логи
          </Button>
          {/* 
    <Button
      data-test-id="reset-form-button"
      type="button"
      className="flex-[1]"
      variant="secondary"
      onClick={onReset}
    >
      Сбросить
    </Button> 
    */}
        </div>
      </form>
    </Form>
  );
};

export { LogExplainForm };
