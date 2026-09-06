import { useEffect, useMemo, useState } from "react";
import { api } from "../services/api";
import type { Game } from "../services/types";
import { buildRow, weekdayOf } from "../services/model";
import WeekSelector from "../components/WeekSelector";
import ModelSignal from "../components/ModelSignal";
import GameRow from "../components/GameRow";

const SEASON = 2026;

// Simple in-memory cache to avoid re-fetching on back navigation
let cachedGames: Game[] | null = null;

function Home() {
  const [games, setGames] = useState<Game[]>(cachedGames || []);
  const [loading, setLoading] = useState(!cachedGames);
  const [error, setError] = useState<string | null>(null);
  const [selectedWeek, setSelectedWeek] = useState<number | null>(null);
  const [dayFilter, setDayFilter] = useState("ALL");

  useEffect(() => {
    if (cachedGames) {
      return;
    }
    let cancelled = false;
    api
      .get<Game[]>("/games", { params: { season: SEASON } })
      .then((r) => {
        if (!cancelled) {
          cachedGames = r.data;
          setGames(r.data);
        }
      })
      .catch(() => {
        if (!cancelled) setError("The board could not be loaded.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const weeks = useMemo(
    () => [...new Set(games.map((g) => g.week))].sort((a, b) => a - b),
    [games]
  );

  useEffect(() => {
    if (selectedWeek === null && weeks.length > 0) {
      setSelectedWeek(weeks[0]);
    }
  }, [weeks, selectedWeek]);

  const activeWeek = selectedWeek ?? weeks[0] ?? null;

  const weekGames = useMemo(() => {
    if (activeWeek === null) return [];
    return games
      .filter((g) => g.week === activeWeek)
      .sort((a, b) => a.gameday.localeCompare(b.gameday) || a.gameId.localeCompare(b.gameId));
  }, [games, activeWeek]);

  const days = useMemo(() => {
    const seen = new Set<string>();
    const list: string[] = [];
    for (const g of weekGames) {
      const d = weekdayOf(g.gameday);
      if (!seen.has(d)) {
        seen.add(d);
        list.push(d);
      }
    }
    return list;
  }, [weekGames]);

  const rows = useMemo(
    () =>
      weekGames
        .filter((g) => dayFilter === "ALL" || weekdayOf(g.gameday) === dayFilter)
        .map(buildRow),
    [weekGames, dayFilter]
  );

  const topSignal = useMemo(() => {
    const withEdge = rows.filter((r) => r.edge !== null);
    if (withEdge.length === 0) return rows[0] ?? null;
    return withEdge.reduce((max, r) => ((r.edge ?? 0) > (max.edge ?? 0) ? r : max));
  }, [rows]);

  const handleSelectWeek = (week: number) => {
    setSelectedWeek(week);
    setDayFilter("ALL");
  };

  if (loading) {
    return <div className="page-state">Loading the board…</div>;
  }

  if (error || activeWeek === null) {
    return <div className="page-state">{error ?? "No games in the calendar."}</div>;
  }

  return (
    <>
      <WeekSelector
        weeks={weeks}
        selectedWeek={activeWeek}
        onSelectWeek={handleSelectWeek}
        days={days}
        dayFilter={dayFilter}
        onSelectDay={setDayFilter}
        gameCount={weekGames.length}
      />

      {topSignal && <ModelSignal row={topSignal} />}

      <section className="game-list">
        <div className="game-list-head">
          <h2 className="game-list-title">Week {String(activeWeek).padStart(2, "0")} Games</h2>
          <span className="game-list-count">
            {rows.length} Game{rows.length === 1 ? "" : "s"}
            {dayFilter !== "ALL" ? ` · ${dayFilter}` : ""} · Model favorite in lime
          </span>
        </div>

        <div className="game-colhead">
          <span className="ch-day">Day</span>
          <span className="ch-away">Away</span>
          <span className="ch-mid">Model Probability</span>
          <span className="ch-home">Home</span>
          <span className="ch-rail">Signal</span>
        </div>

        {rows.map((row) => (
          <GameRow key={row.game.gameId} row={row} />
        ))}
      </section>
    </>
  );
}

export default Home;