import * as React from "react"
import {
  ChevronDownIcon,
  ChevronUpIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
} from "lucide-react"
import { DayButton, DayPicker, getDefaultClassNames } from "react-day-picker"

import { cn } from "@/lib/utils"
import { Button, buttonVariants } from "@/components/ui/button"

function Calendar({
  className,
  classNames,
  showOutsideDays = true,
  captionLayout = "label",
  buttonVariant = "ghost",
  formatters,
  components,
  ...props
}: React.ComponentProps<typeof DayPicker> & {
  buttonVariant?: React.ComponentProps<typeof Button>["variant"]
}) {
  const defaultClassNames = getDefaultClassNames()

  return (
    <DayPicker
      showOutsideDays={showOutsideDays}
      className={cn(
        "bg-background group/calendar p-3 [--cell-size:--spacing(8)] [[data-slot=card-content]_&]:bg-transparent [[data-slot=popover-content]_&]:bg-transparent",
        String.raw`rtl:**:[.rdp-button\_next>svg]:rotate-180`,
        String.raw`rtl:**:[.rdp-button\_previous>svg]:rotate-180`,
        className
      )}
      captionLayout={captionLayout}
      formatters={{
        formatMonthDropdown: (date) =>
          { const localed = date.toLocaleDateString("default", { month: "long"});
            return localed[0].toUpperCase() + localed.substring(1)},
        ...formatters,
      }}
      classNames={{
        
        root: cn("w-[276px]", defaultClassNames.root),
        months: cn(
          "flex gap-4 flex-col md:flex-row relative",
          defaultClassNames.months
        ),
        month: cn("flex flex-col w-full gap-4", defaultClassNames.month),
        nav: cn(
          "flex items-center gap-1 w-full absolute top-0 inset-x-0 justify-between",
          defaultClassNames.nav
        ),
        button_previous: "hidden",
        button_next: "hidden",
        month_caption: cn(
          "flex items-center justify-center w-full",
          defaultClassNames.month_caption
        ),
        dropdowns: cn(
          "w-full flex items-center text-sm font-medium justify-center gap-1.5",
          defaultClassNames.dropdowns
        ),
        dropdown_root: cn(
          "relative has-focus:border-ring border border-input shadow-xs has-focus:ring-ring/50 has-focus:ring-[3px] rounded-md",
          defaultClassNames.dropdown_root
        ),
        dropdown: cn(
          "absolute bg-popover inset-0 opacity-0",
          defaultClassNames.dropdown
        ),
        caption_label: cn(
          "select-none font-medium",
          captionLayout === "label"
            ? "text-sm"
            : "rounded-md pl-2 pr-1 flex items-center gap-1 text-sm h-8 [&>svg]:text-muted-foreground [&>svg]:size-3.5",
          defaultClassNames.caption_label
        ),
        table: "w-full border-collapse",
        weekdays: cn("flex", defaultClassNames.weekdays),
        weekday: cn(
          "text-muted-foreground rounded-md flex-1 font-normal text-[0.8rem] select-none",
          defaultClassNames.weekday
        ),
        week: cn("flex w-full mt-2", defaultClassNames.week),
        week_number_header: cn(
          "select-none w-(--cell-size)",
          defaultClassNames.week_number_header
        ),
        week_number: cn(
          "text-[0.8rem] select-none text-muted-foreground",
          defaultClassNames.week_number
        ),
        day: cn(
          "relative w-full h-full p-0 text-center aspect-square select-none focus:outline-none focus:ring-0 focus-visible:outline-none focus-visible:ring-0",
          defaultClassNames.day
        ),
        range_start: cn(
          "rounded-l-md bg-accent",
          defaultClassNames.range_start
        ),
        range_middle: cn("rounded-none", defaultClassNames.range_middle),
        range_end: cn("rounded-r-md bg-accent", defaultClassNames.range_end),
        today: cn(
          "bg-accent text-accent-foreground rounded-md bg-[#BFDBFE]",
          defaultClassNames.today
        ),
        outside: cn(
          "text-muted-foreground aria-selected:text-muted-foreground",
          defaultClassNames.outside
        ),
        disabled: cn(
          "text-muted-foreground opacity-50",
          defaultClassNames.disabled
        ),
        hidden: cn("invisible", defaultClassNames.hidden),
        ...classNames,
      }}
      components={{
        Root: ({ className, rootRef, ...props }) => {
          return (
            <div
              data-slot="calendar"
              ref={rootRef}
              className={cn(className)}
              {...props}
            />
          )
        },
        Chevron: ({ className, orientation, ...props }) => {
          if (orientation === "left") {
            return (
              <ChevronLeftIcon className={cn("size-4", className)} {...props} />
            )
          }

          if (orientation === "right") {
            return (
              <ChevronRightIcon
                className={cn("size-4", className)}
                {...props}
              />
            )
          }

          return (
            <ChevronDownIcon className={cn("size-4", className)} {...props} />
          )
        },
        DayButton: CalendarDayButton,
        WeekNumber: ({ children, ...props }) => {
          return (
            <td {...props}>
              <div className="flex size-(--cell-size) items-center justify-center text-center">
                {children}
              </div>
            </td>
          )
        },
        MonthsDropdown: ({ options, classNames, value, onChange }) => (
          <MonthYearInputs
            value={Number(value)}
            min={0}
            max={11}
            onChange={onChange!}
            options={options?.map((o) => ({ label: o.label, value: Number(o.value) }))}
            classNames={classNames}
          />
        ),

        YearsDropdown: ({ options, classNames, value, onChange }) => {
          const numericOptions = options?.map((o) => ({ label: o.label, value: Number(o.value) })) || []
          const minYear = numericOptions.length ? Math.min(...numericOptions.map((o) => o.value)) : 1900
          const maxYear = numericOptions.length ? Math.max(...numericOptions.map((o) => o.value)) : 2100
          return (
            <MonthYearInputs
              value={Number(value)}
              min={minYear}
              max={maxYear}
              onChange={onChange!}
              options={numericOptions}
              classNames={classNames}
            />
          )
        },

        ...components,
      }}
      {...props}
    />
  )
}

function CalendarDayButton({
  className,
  day,
  modifiers,
  ...props
}: React.ComponentProps<typeof DayButton>) {
  const defaultClassNames = getDefaultClassNames()

  const ref = React.useRef<HTMLButtonElement>(null)
  React.useEffect(() => {
    if (modifiers.focused) ref.current?.focus()
  }, [modifiers.focused])

  return (
    <Button
      ref={ref}
      variant="ghost"
      size="icon"
      data-day={day.date.toLocaleDateString()}
      data-selected-single={
        modifiers.selected &&
        !modifiers.range_start &&
        !modifiers.range_end &&
        !modifiers.range_middle
      }
      data-range-start={modifiers.range_start}
      data-range-end={modifiers.range_end}
      data-range-middle={modifiers.range_middle}
      className={cn(
        "relative w-full h-full p-0 text-center select-none focus:outline-none focus:ring-0",
        modifiers.selected && "bg-[#2463EB] text-[#FAFAFA]",
        modifiers.today && !modifiers.selected && "bg-[#BFDBFE] text-black",
        className
      )}
      {...props}
    />
  )
}


type MonthYearInputsProps = {
  value: number
  min: number
  max: number
  onChange: (event: React.ChangeEvent<HTMLSelectElement>) => void
  options?: { label: string; value: number }[]
  classNames?: any
}

function MonthYearInputs({
  value,
  min,
  max,
  onChange,
  options,
  classNames,
}: MonthYearInputsProps) {
  function createSyntheticEvent(newValue: number) {
    return {
      target: { value: newValue.toString() },
    } as React.ChangeEvent<HTMLSelectElement>
  }

  return (
    <div
      className={cn("flex w-full gap-2 h-[28px]", classNames?.dropdown_root)}
      tabIndex={-1} // <- убираем попадание в фокус
    >
      <div
        className="pl-2 w-full bg-transparent border-0 p-0 m-0 outline-none select-none flex items-center"
        aria-label="Value"
      >
        {options?.find((o) => o.value === value)?.label ?? value.toString()}
      </div>
      <div className="pr-2 flex flex-col items-center justify-center">
        <button
          type="button"
          tabIndex={-1}
          onClick={() => onChange(createSyntheticEvent(value - 1 < min ? max : value - 1))}
          className="p-0 m-0 text-sm select-none flex items-center justify-center"
          aria-label="Decrease"
        >
          <ChevronUpIcon size={12} className="cursor-pointer" />
        </button>
        <button
          type="button"
          tabIndex={-1}
          onClick={() => onChange(createSyntheticEvent(value + 1 > max ? min : value + 1))}
          className="p-0 m-0 text-sm select-none flex items-center justify-center"
          aria-label="Increase"
        >
          <ChevronDownIcon size={12} className="cursor-pointer" />
        </button>
      </div>
    </div>
  )
}





export { Calendar, CalendarDayButton }
