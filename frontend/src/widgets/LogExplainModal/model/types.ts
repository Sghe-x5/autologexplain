import * as z from "zod";

export const logFormSchema = z
  .object({
    service: z.string().nonempty("Выберите сервис"),
    userID: z.string().min(1, "Введите имя пользователя"),
    startTime: z.date(),
    endTime: z.date(),
  })
  .refine((data) => data.startTime <= data.endTime, {
    message: "Время начала должно быть меньше или равно времени окончания",
    path: ["startTime"],
  })
  .refine((data) => data.startTime < new Date(), {
    message: "Время начала должно быть в прошлом",
    path: ["startTime"],
  })
  .refine((data) => data.endTime < new Date(), {
    message: "Время окончания должно быть в прошлом",
    path: ["endTime"],
  });

type LogExplanation = z.infer<typeof logFormSchema>;
export type { LogExplanation };

export interface UserLogExplanation {
  userId: number;
  period: string | null;
  service: string;
  visits: number;
  sessionDurationSeconds: number;
  sessionDurationReadable: string;
  purchases: {
    count: number;
    totalAmount: number;
  };
  refunds: {
    count: number;
    totalAmount: number;
  };
  summary: string;
}
