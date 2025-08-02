import * as React from "react"
import { CalendarIcon } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover"
import TimePicker from "../TimePicker/TimePicker"
export default function DatePicker({ label }: DatePickerProps) {
  const [open, setOpen] = React.useState(false)
  const [date, setDate] = React.useState<Date | undefined>(undefined)
  const [month, setMonth] = React.useState<Date | undefined>(undefined)
  const [time, setTime] = React.useState<{ hours: number; minutes: number } | undefined>(undefined)
  const [value, setValue] = React.useState("")

  function handleDateChange(newDate: Date | undefined) {
    if (!newDate) return
    setDate(newDate)
    setMonth(newDate)
    updateFormattedValue(newDate, time)
  }

  function handleTimeChange(newTime: { hours: number; minutes: number }) {
    setTime(newTime)
    updateFormattedValue(date, newTime)
  }

  function updateFormattedValue(
    d: Date | undefined,
    t: { hours: number; minutes: number } | undefined
  ) {
    if (!d) {
      setValue("")
      return
    }
    const formatted = formatDateWithTime(d, t)
    setValue(formatted)
  }

  return (
    <div className="flex flex-col gap-3">
      <Label htmlFor="date" className="px-1">
        {label}
      </Label>
      <div className="relative flex gap-2">
        <Input
          id="date"
          value={value}
          placeholder="дд.мм.гггг --:--"
          className="bg-background pr-10"
          onChange={(e) => {
            setValue(e.target.value)
          }}
          onKeyDown={(e) => {
            if (e.key === "ArrowDown") {
              e.preventDefault()
              setOpen(true)
            }
          }}
        />
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <Button
              id="date-picker"
              variant="ghost"
              className="absolute top-1/2 right-2 size-6 -translate-y-1/2"
            >
              <CalendarIcon className="size-3.5" />
              <span className="sr-only">Select date</span>
            </Button>
          </PopoverTrigger>
          <PopoverContent
            className="w-auto overflow-hidden p-0"
            align="end"
            alignOffset={-8}
            sideOffset={10}
          >
            <Calendar
              mode="single"
              selected={date}
              captionLayout="dropdown"
              month={month}
              onMonthChange={setMonth}
              onSelect={handleDateChange}
            />
            <TimePicker value={time} onChange={handleTimeChange} />
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
  const hh = time ? String(time.hours).padStart(2, "0") : "--"
  const min = time ? String(time.minutes).padStart(2, "0") : "--"
  return `${dd}.${mm}.${yyyy} ${hh}:${min}`
}

type DatePickerProps = {
    label?: string;
};