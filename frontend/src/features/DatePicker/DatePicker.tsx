import * as React from "react"
import { CalendarIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { ru } from "date-fns/locale"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import TimePicker from "../TimePicker/TimePicker"

export default function DatePicker({ label, value, onChange }: DatePickerProps) {
  const [open, setOpen] = React.useState(false)
  const [internalDate, setInternalDate] = React.useState<Date | undefined>(value)
  const [month, setMonth] = React.useState<Date | undefined>(value)
  const [time, setTime] = React.useState<{ hours: number; minutes: number } | undefined>(
    value ? { hours: value.getHours(), minutes: value.getMinutes() } : undefined
  )
  const [formattedValue, setFormattedValue] = React.useState("")

  React.useEffect(() => {
    if (value) {
      setInternalDate(value)
      setTime({ hours: value.getHours(), minutes: value.getMinutes() })
      setFormattedValue(formatDateWithTime(value, {
        hours: value.getHours(),
        minutes: value.getMinutes(),
      }))
    } else {
      setInternalDate(undefined)
      setTime(undefined)
      setFormattedValue("")
    }
  }, [value])

  const handleClear = () => {
    setInternalDate(undefined)
    setTime(undefined)
    setFormattedValue("")
    onChange?.(undefined as any) // form.reset() triggers this
    setOpen(false)
  }

  const handleToday = () => {
    const now = new Date()
    setInternalDate(now)
    setMonth(now)
    const t = { hours: now.getHours(), minutes: now.getMinutes() }
    setTime(t)
    setFormattedValue(formatDateWithTime(now, t))
    onChange?.(mergeDateTime(now, t))
  }

  const handleDateChange = (newDate: Date | undefined) => {
    if (!newDate) return
    setInternalDate(newDate)
    setMonth(newDate)
    const newDT = mergeDateTime(newDate, time)
    setFormattedValue(formatDateWithTime(newDate, time))
    onChange?.(newDT)
  }

  const handleTimeChange = (newTime: { hours: number; minutes: number }) => {
    setTime(newTime)
    const newDT = mergeDateTime(internalDate ?? new Date(), newTime)
    setFormattedValue(formatDateWithTime(internalDate, newTime))
    onChange?.(newDT)
  }

  return (
    <div className="flex flex-col gap-3">
      {label && <Label htmlFor="date" className="px-1">{label}</Label>}
      <div className="relative flex gap-2">
        <Input
          data-test-id="date-input"
          id="date"
          value={formattedValue}
          placeholder="дд.мм.гггг --:--"
          className="bg-background pr-10"
          readOnly
        />
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              data-test-id="reveal-date-inputs-button"
              id="date-picker"
              variant="ghost"
              className="absolute top-1/2 right-2 size-6 -translate-y-1/2"
            >
              <CalendarIcon className="size-3.5" />
              <span className="sr-only">Select date</span>
            </Button>
          </PopoverTrigger>
          <PopoverContent
            className="flex w-auto overflow-hidden border p-0 bg-white dark:bg-gray-800"
            align="end"
            alignOffset={-8}
            sideOffset={10}
          >
            <div className="h-[370px] flex flex-col justify-between border-r">
              <Calendar
                mode="single"
                selected={internalDate}
                captionLayout="dropdown"
                month={month}
                onMonthChange={setMonth}
                onSelect={handleDateChange}
                weekStartsOn={1}
                locale={ru}
              />
              <div className="flex justify-between px-4 py-1">
                <Button
                  data-test-id="clear-date-button"
                  variant="ghost"
                  size="sm"
                  onClick={handleClear}
                  className="text-destructive hover:text-destructive/80 cursor-pointer"
                >
                  Очистить
                </Button>
                <Button
                  data-test-id="set-today-button"
                  variant="ghost"
                  size="sm"
                  onClick={handleToday}
                  className="text-primary hover:text-primary/80 cursor-pointer"
                >
                  Сегодня
                </Button>
              </div>
            </div>
            <div className="px-1 pb-[10px]">
              <TimePicker value={time} onChange={handleTimeChange} />
            </div>
          </PopoverContent>
        </Popover>
      </div>
    </div>
  )
}

function formatDateWithTime(
  date: Date | undefined,
  time?: { hours: number; minutes: number }
) {
  if (!date) return ""
  const dd = String(date.getDate()).padStart(2, "0")
  const mm = String(date.getMonth() + 1).padStart(2, "0")
  const yyyy = date.getFullYear()
  const timePart = time
    ? `${String(time.hours).padStart(2, "0")}:${String(time.minutes).padStart(2, "0")}`
    : "--:--"
  return `${dd}.${mm}.${yyyy} ${timePart}`
}

function mergeDateTime(date: Date, time?: { hours: number; minutes: number }) {
  if (!time) return date
  const newDate = new Date(date)
  newDate.setHours(time.hours)
  newDate.setMinutes(time.minutes)
  newDate.setSeconds(0)
  newDate.setMilliseconds(0)
  return newDate
}

type DatePickerProps = {
  label?: string
  value?: Date
  onChange?: (value: Date) => void
}
