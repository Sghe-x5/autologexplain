'use client'

import { useEffect, useRef, useState } from "react"

interface TimePickerProps {
  value?: { hours: number; minutes: number }
  onChange?: (time: { hours: number; minutes: number }) => void
}

const TimePicker = ({ value, onChange }: TimePickerProps) => {
    const time = {
      hours: value?.hours ?? 0,
      minutes: value?.minutes ?? 0,
  }

  const hours = Array.from({ length: 24 }, (_, i) => i)
  const minutes = Array.from({ length: 60 }, (_, i) => i)
  const repeatedHours = [...hours, ...hours, ...hours]
  const repeatedMinutes = [...minutes, ...minutes, ...minutes]

  const hourRef = useRef<HTMLDivElement>(null)
  const minuteRef = useRef<HTMLDivElement>(null)

  const itemHeight = 36
  const middleIndexHours = hours.length
  const middleIndexMinutes = minutes.length

  useEffect(() => {
    if (hourRef.current) {
      hourRef.current.scrollTop = middleIndexHours * itemHeight
    }
    if (minuteRef.current) {
      minuteRef.current.scrollTop = middleIndexMinutes * itemHeight
    }
  }, [])

  const loopScroll = (ref: React.RefObject<HTMLDivElement | null>, totalItems: number) => {
    if (!ref.current) return
    const scrollTop = ref.current.scrollTop
    const totalHeight = totalItems * itemHeight

    if (scrollTop <= itemHeight) {
      ref.current.scrollTop = scrollTop + totalHeight
    } else if (scrollTop >= totalHeight * 2) {
      ref.current.scrollTop = scrollTop - totalHeight
    }
  }

  const handleClickHour = (h: number) => {
    const updated = { ...time, hours: h }
    onChange?.(updated)
  }

  const handleClickMinute = (m: number) => {
    const updated = { ...time, minutes: m }
    onChange?.(updated)
  }

  return (
    <div className="flex gap-1 h-[300px] items-center px-1 py-1">
      <div
        ref={hourRef}
        className="flex-1 h-full overflow-y-auto scrollbar-hide text-center"
        onScroll={() => loopScroll(hourRef, hours.length)}
      >
        {repeatedHours.map((h, i) => (
          <div
            key={`h-${i}`}
            onClick={() => handleClickHour(h)}
            className={`cursor-pointer px-4 py-2 h-9 flex items-center justify-center text-sm rounded-md transition-colors duration-200 ${
              h === time.hours ? "bg-blue-500 text-white" : "hover:bg-gray-200 dark:hover:bg-gray-700"
            }`}
          >
            {h.toString().padStart(2, "0")}
          </div>
        ))}
      </div>
      <div
        ref={minuteRef}
        className="flex-1 h-full overflow-y-auto scrollbar-hide text-center"
        onScroll={() => loopScroll(minuteRef, minutes.length)}
      >
        {repeatedMinutes.map((m, i) => (
          <div
            key={`m-${i}`}
            onClick={() => handleClickMinute(m)}
            className={`cursor-pointer px-4 py-2 h-9 flex items-center justify-center text-sm rounded-md transition-colors duration-200 ${
              m === time.minutes ? "bg-blue-500 text-white" : "hover:bg-gray-200 dark:hover:bg-gray-700"
            }`}
          >
            {m.toString().padStart(2, "0")}
          </div>
        ))}
      </div>
    </div>
  )
}

export default TimePicker
