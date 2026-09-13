import { useMemo, useState } from "react";
import { usePublication } from "../services/publicationContext";
import { buildRow, weekdayOf } from "../services/model";
import WeekSelector from "../components/WeekSelector";
import ModelSignal from "../components/ModelSignal";
import GameRow from "../components/GameRow";

function Home() {
  const { publication, games, loading, error, retry, selectedWeek, selectWeek } = usePublication();
  const [dayFilter, setDayFilter] = useState("ALL");

  const weeks = useMemo(
    () => [...new Set(games.map((g) => g.week))].sort((a, b) => a - b),
    [games]
  );

  const activeWeek = selectedWeek ?? weeks[0] ?? null;

  const weekGames = useMemo(() => {
    if (activeWeek === null) return [];
    return games
      .filter((g) => g.week === activeWeek)
      .sort((a, b) => (a.gameday ?? "").localeCompare(b.gameday ?? "") || a.gameId.localeCompare(b.gameId));
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
    if (withEdge.length === 0) return null;
    return withEdge.reduce((max, r) => ((r.edge ?? 0) > (max.edge ?? 0) ? r : max));
  }, [rows]);

  const handleSelectWeek = (week: number) => {
    selectWeek(week);
    setDayFilter("ALL");
  };

  if (loading) {
    return <div className="page-state">Loading the board…</div>;
  }

  if (error) {
    return (
      <div className="page-state page-state-error" role="alert">
        <p>{error}</p>
        <button className="page-state-retry" type="button" onClick={retry}>
          Retry
        </button>
      </div>
    );
  }

  if (activeWeek === null) {
    return <div className="page-state">No games are scheduled for this season yet.</div>;
  }

  return (
    <>
      <WeekSelector
        season={publication?.defaultSeason ?? null}
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
            {dayFilter !== "ALL" ? ` · ${dayFilter}` : ""}{topSignal ? " · Market favorite in lime" : ""}
          </span>
        </div>

        <div className="game-colhead">
          <span className="ch-day">Day</span>
          <span className="ch-away">Away</span>
          <span className="ch-mid">{rows.some((row) => row.homePct !== null) ? "Market probability" : "Market availability"}</span>
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
