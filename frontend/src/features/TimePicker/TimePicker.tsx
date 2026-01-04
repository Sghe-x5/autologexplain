'use client'

import { useEffect, useState } from 'react'

interface TimePickerProps {
  label?: string
  value?: { hours: number; minutes: number }
  onChange?: (time: { hours: number; minutes: number }) => void
}

const TimePicker = ({ label, value, onChange }: TimePickerProps) => {
  const [time, setTime] = useState({
    hours: value?.hours ?? 0,
    minutes: value?.minutes ?? 0,
  })

  useEffect(() => {
    if (onChange) {
      onChange(time)
    }
  }, [time])

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const [h, m] = e.target.value.split(':').map(Number)
    setTime({ hours: h, minutes: m })
  }

  return (
    <>
      {label && (
        <label
          htmlFor="start-time"
          className="block mb-2 text-sm font-medium text-gray-900 dark:text-white"
        >
          {label}
        </label>
      )}
      <input
        type="time"
        id="start-time"
        className="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-blue-500 focus:border-blue-500 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-blue-500 dark:focus:border-blue-500"
        value={`${time.hours.toString().padStart(2, '0')}:${time.minutes
          .toString()
          .padStart(2, '0')}`}
        onChange={handleChange}
        min="00:00"
        max="23:59"
      />
    </>
  )
}

export default TimePicker
