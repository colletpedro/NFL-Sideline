import type { Game } from "./types";

/** Calendar dates are compared in UTC, inclusively; odds never affect week selection. */
export function initialWeek(games: Pick<Game, "week" | "gameday">[], today: Date): number | null {
  const weeks = [...new Set(games.map((game) => game.week))].sort((a, b) => a - b);
  if (!weeks.length) return null;
  const day = today.toISOString().slice(0, 10);
  const intervals = weeks.map((week) => {
    const dates = games.filter((game) => game.week === week && game.gameday)
      .map((game) => game.gameday!).sort();
    return { week, start: dates[0], end: dates[dates.length - 1] };
  }).filter((interval) => interval.start);
  return intervals.find((interval) => interval.start <= day && day <= interval.end)?.week
    ?? intervals.find((interval) => interval.start > day)?.week
    ?? weeks[weeks.length - 1];
}
