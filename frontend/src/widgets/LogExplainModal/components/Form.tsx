import { Input } from "@/components/ui/input";
import DatePicker from "@/features/DatePicker";
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

import * as z from "zod";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm, Controller } from "react-hook-form";
import { Calendar, CloudLightningIcon, User } from "lucide-react";

const formSchema = z.object({
  service: z.string().nonempty("Выберите сервис"),
  userID: z.string().min(1, "Введите имя пользователя"),
  startTime: z.date(),
  endTime: z.date(),
});

const LogExplainForm = () => {
  const form = useForm<z.infer<typeof formSchema>>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      service: "",
      userID: "",
      startTime: new Date(),
      endTime: new Date(),
    },
  });

  const onSubmit = (values: z.infer<typeof formSchema>) => {
    alert(JSON.stringify(values, null, 2));
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
                <CloudLightningIcon />
                Выберите сервис
              </FormLabel>
              <Select onValueChange={field.onChange} value={field.value}>
                <FormControl>
                  <SelectTrigger>
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
                    <DatePicker value={field.value} onChange={field.onChange} />
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
                    <DatePicker value={field.value} onChange={field.onChange} />
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
            onClick={() => form.reset()}
          >
            Сбросить
          </Button>
        </div>
      </form>
    </Form>
  );
};

export { LogExplainForm };
