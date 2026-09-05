import { ChevronLeft, ChevronRight } from "lucide-react";

interface WeekSelectorProps {
  weeks: number[];
  selectedWeek: number;
  onSelectWeek: (week: number) => void;
  /** Distinct weekdays in the selected week, e.g. ["WED","THU","SUN","MON"]. */
  days: string[];
  dayFilter: string;
  onSelectDay: (day: string) => void;
  gameCount: number;
}

function WeekSelector({
  weeks,
  selectedWeek,
  onSelectWeek,
  days,
  dayFilter,
  onSelectDay,
  gameCount,
}: WeekSelectorProps) {
  const idx = weeks.indexOf(selectedWeek);
  const prev = idx > 0 ? weeks[idx - 1] : null;
  const next = idx >= 0 && idx < weeks.length - 1 ? weeks[idx + 1] : null;

  return (
    <div className="weekbar">
      <div className="weeknav">
        <button
          className="week-btn"
          disabled={prev === null}
          onClick={() => prev !== null && onSelectWeek(prev)}
          aria-label="Previous week"
        >
          <ChevronLeft size={13} strokeWidth={2.5} />
          Prev Week
        </button>
        <div className="week-label">
          <span className="w">Week {String(selectedWeek).padStart(2, "0")}</span>
          <span className="s">
            {gameCount} games · 2026
          </span>
        </div>
        <button
          className="week-btn"
          disabled={next === null}
          onClick={() => next !== null && onSelectWeek(next)}
          aria-label="Next week"
        >
          Next Week
          <ChevronRight size={13} strokeWidth={2.5} />
        </button>
      </div>

      <div className="daytabs" role="tablist" aria-label="Filter by day">
        <button
          className={`daytab ${dayFilter === "ALL" ? "active" : ""}`}
          onClick={() => onSelectDay("ALL")}
        >
          All
        </button>
        {days.map((d) => (
          <button
            key={d}
            className={`daytab ${dayFilter === d ? "active" : ""}`}
            onClick={() => onSelectDay(d)}
          >
            {d}
          </button>
        ))}
      </div>
    </div>
  );
}

export default WeekSelector;