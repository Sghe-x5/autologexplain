import { Input } from "@/components/ui/input";
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
import { Calendar, Zap, User } from "lucide-react";
import { Separator } from "@/components/ui/separator";
import {
  logFormSchema,
  type LogExplanation,
  type UserLogExplanation,
} from "../model/types";
import { useLogStore } from "../model/store";
import { getPeriod } from "@/lib/getPeriod";

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
  const resetLog = useLogStore((state) => state.reset);

  const onSubmit = (values: LogExplanation) => {
    mockData.userId = Number(values.userID);
    mockData.period = getPeriod({
      startTime: values.startTime,
      endTime: values.endTime,
    });

    setLog(mockData);
  };

  const onReset = () => {
    form.reset();
    resetLog();
  };

  return (
    <Form {...form}>
      <form
        onSubmit={form.handleSubmit(onSubmit)}
        className="space-y-4 flex flex-col gap-4"
      >
        <FormField
          control={form.control}
          name="service"
          render={({ field }) => (
            <FormItem>
              <FormLabel>
                <Zap />
                Выберите сервис
              </FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger className="w-full">
                    <SelectValue placeholder="Выберите сервис для анализа" />
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

        <FormItem>
          <FormLabel>
            <Calendar className="inline-block mr-2" />
            Временной диапазон
          </FormLabel>
          <div className="flex flex-col gap-4">
            <FormField
              control={form.control}
              name="startTime"
              render={({ field }) => (
                <FormItem className="w-full">
                  <FormLabel>Время начала</FormLabel>
                  <FormControl>
                    <DatePicker label={""} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="endTime"
              render={({ field }) => (
                <FormItem className="w-full">
                  <FormLabel>Время окончания</FormLabel>
                  <FormControl>
                    <DatePicker label={""} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
          </div>
        </FormItem>

        <FormField
          control={form.control}
          name="userID"
          render={({ field }) => (
            <FormItem>
              <FormLabel>
                <User /> ID пользователя
              </FormLabel>
              <FormControl>
                <Input
                  placeholder="Введите userId, sessionId или идентификатор"
                  {...field}
                />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />

        <Separator />

        <div className="flex  gap-2">
          <Button
            type="submit"
            className="flex-11/12"
            disabled={!form.formState.isValid || form.formState.isSubmitting}
          >
            Анализировать логи
          </Button>
          <Button
            type="button"
            className="flex-1/12"
            variant="secondary"
            onClick={onReset}
          >
            Сбросить
          </Button>
        </div>
      </form>
    </Form>
  );
};

export { LogExplainForm };
