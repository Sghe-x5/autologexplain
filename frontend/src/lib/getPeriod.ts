interface getPeriod {
  startTime: Date;
  endTime: Date;
}
export const getPeriod = (values: getPeriod) => {
  return `${values.startTime.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })} — ${values.endTime.toLocaleString("ru-RU", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })}`;
};
