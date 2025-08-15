import { ChevronDownIcon, ChevronUpIcon } from "lucide-react";
import { useEffect, useRef } from "react";

interface TimePickerProps {
  value?: { hours: number; minutes: number };
  onChange?: (time: { hours: number; minutes: number }) => void;
}

// const clamp = (num: number, min: number, max: number) =>
//   Math.min(Math.max(num, min), max);

const TimePicker = ({ value, onChange }: TimePickerProps) => {
  const time = {
    hours: value?.hours ?? 0,
    minutes: value?.minutes ?? 0,
  };

  const hours = Array.from({ length: 24 }, (_, i) => i);
  const minutes = Array.from({ length: 60 }, (_, i) => i);
  const repeatedHours = [...hours, ...hours, ...hours];
  const repeatedMinutes = [...minutes, ...minutes, ...minutes];

  const hourRef = useRef<HTMLDivElement>(null);
  const minuteRef = useRef<HTMLDivElement>(null);

  const itemHeight = 36;
  const middleIndexHours = hours.length;
  const middleIndexMinutes = minutes.length;

  useEffect(() => {
    if (hourRef.current) {
      hourRef.current.scrollTop =
        middleIndexHours * itemHeight + (time.hours * itemHeight) / 3;
    }
    if (minuteRef.current) {
      minuteRef.current.scrollTop =
        middleIndexMinutes * itemHeight + (time.minutes * itemHeight) / 3;
    }
  }, [
    middleIndexHours,
    middleIndexMinutes,
    time.hours,
    time.minutes,
    itemHeight,
  ]);

  const loopScroll = (
    ref: React.RefObject<HTMLDivElement | null>,
    totalItems: number
  ) => {
    if (!ref.current) return;
    const scrollTop = ref.current.scrollTop;
    const totalHeight = totalItems * itemHeight;

    if (scrollTop <= itemHeight) {
      ref.current.scrollTop = scrollTop + totalHeight;
    } else if (scrollTop >= totalHeight * 2) {
      ref.current.scrollTop = scrollTop - totalHeight;
    }
  };

  const handleClickHour = (h: number) => {
    onChange?.({ ...time, hours: h });
  };

  const handleClickMinute = (m: number) => {
    onChange?.({ ...time, minutes: m });
  };

  const incrementHours = () => {
    const newH = (time.hours + 1) % 24;
    onChange?.({ ...time, hours: newH });
  };
  const decrementHours = () => {
    const newH = (time.hours - 1 + 24) % 24;
    onChange?.({ ...time, hours: newH });
  };
  const incrementMinutes = () => {
    let newM = time.minutes + 1;
    let newH = time.hours;
    if (newM >= 60) {
      newM = 0;
      newH = (newH + 1) % 24;
    }
    onChange?.({ hours: newH, minutes: newM });
  };
  const decrementMinutes = () => {
    let newM = time.minutes - 1;
    let newH = time.hours;
    if (newM < 0) {
      newM = 59;
      newH = (newH - 1 + 24) % 24;
    }
    onChange?.({ hours: newH, minutes: newM });
  };

  return (
    <div className="flex flex-col gap-4 p-3">
      <div className="flex justify-center items-center gap-2">
        <div
          className="flex w-14 h-[28px] relative border border-input rounded-md shadow-xs select-none"
          tabIndex={-1}
          aria-label="Hours"
        >
          <div className="flex-1 pl-2 flex items-center bg-transparent">
            {time.hours.toString().padStart(2, "0")}
          </div>
          <div className="flex flex-col items-center justify-center pr-2">
            <button
              type="button"
              tabIndex={-1}
              onClick={incrementHours}
              aria-label="Increase hours"
              className="p-0 m-0 text-sm flex items-center justify-center cursor-pointer"
            >
              <ChevronUpIcon className="w-3 h-3" aria-hidden="true" />
            </button>
            <button
              type="button"
              tabIndex={-1}
              onClick={decrementHours}
              aria-label="Decrease hours"
              className="p-0 m-0 text-sm flex items-center justify-center cursor-pointer"
            >
              <ChevronDownIcon className="w-3 h-3" aria-hidden="true" />
            </button>
          </div>
        </div>

        <span className="text-xl font-semibold select-none relative top-[-2px]">
          :
        </span>

        <div
          className="flex w-14 h-[28px] relative border border-input rounded-md shadow-xs select-none"
          tabIndex={-1}
          aria-label="Minutes"
        >
          <div className="flex-1 pl-2 flex items-center bg-transparent">
            {time.minutes.toString().padStart(2, "0")}
          </div>
          <div className="flex flex-col items-center justify-center pr-2">
            <button
              type="button"
              tabIndex={-1}
              onClick={incrementMinutes}
              aria-label="Increase minutes"
              className="p-0 m-0 text-sm flex items-center justify-center cursor-pointer"
            >
              <ChevronUpIcon className="w-3 h-3" aria-hidden="true" />
            </button>
            <button
              type="button"
              tabIndex={-1}
              onClick={decrementMinutes}
              aria-label="Decrease minutes"
              className="p-0 m-0 text-sm flex items-center justify-center cursor-pointer"
            >
              <ChevronDownIcon className="w-3 h-3" aria-hidden="true" />
            </button>
          </div>
        </div>
      </div>

      <div className="flex gap-1 h-[250px] items-center">
        <div
          data-test-id="input-hour-div"
          ref={hourRef}
          className="flex-1 h-full overflow-y-auto scrollbar-hide text-center"
          onScroll={() => loopScroll(hourRef, hours.length)}
        >
          {repeatedHours.map((h, i) => (
            <div
              key={`h-${i}`}
              onClick={() => handleClickHour(h)}
              className={`cursor-pointer px-4 py-1 h-8 mb-1 flex items-center justify-center text-sm rounded-md transition-colors duration-200 ${
                h === time.hours
                  ? "bg-blue-500 text-white"
                  : "hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              {h.toString().padStart(2, "0")}
            </div>
          ))}
        </div>
        <div
          data-test-id="input-minute-div"
          ref={minuteRef}
          className="flex-1 h-full overflow-y-auto scrollbar-hide text-center"
          onScroll={() => loopScroll(minuteRef, minutes.length)}
        >
          {repeatedMinutes.map((m, i) => (
            <div
              key={`m-${i}`}
              onClick={() => handleClickMinute(m)}
              className={`cursor-pointer px-4 py-1 h-8 mb-1 flex items-center justify-center text-sm rounded-md transition-colors duration-200 ${
                m === time.minutes
                  ? "bg-blue-500 text-white"
                  : "hover:bg-gray-200 dark:hover:bg-gray-700"
              }`}
            >
              {m.toString().padStart(2, "0")}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TimePicker;
