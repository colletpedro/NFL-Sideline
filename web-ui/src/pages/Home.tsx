import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";
import ProbabilitySplit from "../components/ProbabilitySplit";
import type { Game, GameDetail } from "../services/types";
import { fairProbability, favoriteOf, fmtLine } from "../services/types";

const SEASON = 2026;

interface BoardRow {
  game: Game;
  favAbbr: string;
  dogAbbr: string;
  favPct: number | null;
  dogPct: number | null;
}

function buildRow(game: Game): BoardRow {
  const fav = favoriteOf(game);
  const dog = fav === game.homeTeam ? game.awayTeam : game.homeTeam;
  const fair = fairProbability(game.homeMoneyline, game.awayMoneyline);
  const favPct =
    fair !== null && fair.home !== null && fair.away !== null
      ? (fav === game.homeTeam ? fair.home : fair.away) * 100
      : null;
  const dogPct = favPct !== null ? 100 - favPct : null;
  return { game, favAbbr: fav.teamAbbr, dogAbbr: dog.teamAbbr, favPct, dogPct };
}

function Home() {
  const [games, setGames] = useState<Game[]>([]);
  const [featuredDetail, setFeaturedDetail] = useState<GameDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    api
      .get<Game[]>("/games", { params: { season: SEASON } })
      .then((r) => {
        if (!cancelled) setGames(r.data);
      })
      .catch(() => {
        if (!cancelled) setError("The board could not be composed.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  /** A edição da semana: a primeira semana com jogos no calendário. */
  const edition = useMemo(() => {
    if (games.length === 0) return null;
    const week = Math.min(...games.map((g) => g.week));
    const list = games
      .filter((g) => g.week === week)
      .sort((a, b) => a.gameday.localeCompare(b.gameday) || a.gameId.localeCompare(b.gameId));
    return { week, list };
  }, [games]);

  /** Capa da edição: o jogo com a linha mais forte (maior confiança). */
  const featured = useMemo(() => {
    if (!edition) return null;
    const withLine = edition.list.filter((g) => g.spreadLine !== null);
    if (withLine.length === 0) return edition.list[0] ?? null;
    return withLine.reduce((max, g) =>
      Math.abs(g.spreadLine as number) > Math.abs(max.spreadLine as number) ? g : max
    );
  }, [edition]);

  useEffect(() => {
    if (!featured) return;
    let cancelled = false;
    api
      .get<GameDetail>(`/games/${featured.gameId}`)
      .then((r) => {
        if (!cancelled) setFeaturedDetail(r.data);
      })
      .catch(() => {
        /* capa usa probabilidade derivada da moneyline se o mercado faltar */
      });
    return () => {
      cancelled = true;
    };
  }, [featured?.gameId]);

  const rows: BoardRow[] = useMemo(() => (edition ? edition.list.map(buildRow) : []), [edition]);

  const dateRange = useMemo(() => {
    if (!edition) return "";
    const days = [...new Set(edition.list.map((g) => g.gameday))].sort();
    const month = new Date(`${days[0]}T00:00:00Z`).toLocaleDateString("en-US", {
      timeZone: "UTC",
      month: "long",
    });
    const first = new Date(`${days[0]}T00:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", day: "2-digit" });
    const last = new Date(`${days[days.length - 1]}T00:00:00Z`).toLocaleDateString("en-US", { timeZone: "UTC", day: "2-digit" });
    return `${first}–${last} ${month.toUpperCase()} ${SEASON}`;
  }, [edition]);

  const teamCount = useMemo(() => {
    if (!edition) return 0;
    return new Set(edition.list.flatMap((g) => [g.homeTeam.teamAbbr, g.awayTeam.teamAbbr])).size;
  }, [edition]);

  if (loading) {
    return <div className="page-state">Composing the edition…</div>;
  }

  if (error || !edition) {
    return <div className="page-state">{error ?? "No games in the calendar."}</div>;
  }

  const featuredRow = featured ? buildRow(featured) : null;
  const featuredMarket = featuredDetail?.market ?? null;
  const featuredHomePct =
    featuredMarket?.homeImpliedFair !== null && featuredMarket?.homeImpliedFair !== undefined
      ? featuredMarket.homeImpliedFair * 100
      : featuredRow?.favPct !== null && featuredRow !== null
        ? featuredRow.favPct
        : null;
  const featuredDogPct = featuredHomePct !== null ? 100 - featuredHomePct : null;
  const featuredFav =
    featuredHomePct !== null && featuredRow !== null
      ? featuredHomePct >= 50
        ? featuredRow.favAbbr
        : featuredRow.dogAbbr
      : null;

  return (
    <>
      <header className="edition">
        <p className="edition-kicker">Week {String(edition.week).padStart(2, "0")}</p>
        <h1 className="edition-title">NFL Forecast</h1>
        <p className="edition-dates">{dateRange}</p>
        <p className="edition-statement">
          {edition.list.length} games. One model. Where the numbers see the strongest edge.
        </p>
      </header>

      {featured && featuredRow && (
        <section className="featured">
          <div>
            <p className="featured-week">Cover Story</p>
            <h2 className="featured-matchup">
              {featured.awayTeam.teamName} <span className="at">@</span>{" "}
              {featured.homeTeam.teamName}
            </h2>
            <p className="featured-stand">
              The widest line on the board. The market's most emphatic signal of the week.
            </p>
            <dl className="featured-meta">
              <div>
                Line {fmtLine(featured.spreadLine)} — Total {featured.totalLine?.toFixed(1) ?? "—"} —{" "}
                {featured.awayTeam.teamAbbr} @ {featured.homeTeam.teamAbbr}
              </div>
            </dl>
          </div>
          <div className="featured-side">
            {featuredHomePct !== null ? (
              <p className="featured-number">
                {featuredHomePct.toFixed(1)}
                <small>%</small>
              </p>
            ) : null}
            <p className="featured-favorite">
              Model favorite <span className="fav">{featuredFav ?? featuredRow.favAbbr}</span>
            </p>
            {featuredHomePct !== null && featuredDogPct !== null && (
              <ProbabilitySplit
                left={{ abbr: featuredFav ?? featuredRow.favAbbr, pct: featuredHomePct }}
                right={{ abbr: featuredFav === featuredRow.favAbbr ? featuredRow.dogAbbr : featuredRow.favAbbr, pct: featuredDogPct }}
                favSide="left"
              />
            )}
          </div>
        </section>
      )}

      <section className="board">
        <div className="board-head">
          <h2 className="board-title">Model Board</h2>
          <span className="board-count">
            {edition.list.length} Games · {teamCount} Teams · Week {String(edition.week).padStart(2, "0")}
          </span>
        </div>
        <div className="board-colhead">
          <span>Matchup</span>
          <span>Model</span>
          <span className="col-num">Spread</span>
          <span className="col-num col-total">Total</span>
        </div>
        {rows.map((row) => (
          <Link
            key={row.game.gameId}
            to={`/game/${row.game.gameId}`}
            className={`game-row ${row.game.gameId === featured?.gameId ? "is-featured" : ""}`}
          >
            <span className="row-matchup">
              {row.game.awayTeam.teamName} <span className="at">@</span>{" "}
              {row.game.homeTeam.teamName}
            </span>
            <span className="row-prob">
              {row.favPct !== null && row.dogPct !== null ? (
                <ProbabilitySplit
                  left={{ abbr: row.favAbbr, pct: row.favPct }}
                  right={{ abbr: row.dogAbbr, pct: row.dogPct }}
                  favSide="left"
                />
              ) : (
                "no line"
              )}
            </span>
            <span className="row-num">{fmtLine(row.game.spreadLine)}</span>
            <span className="row-num row-total">
              {row.game.totalLine !== null ? row.game.totalLine.toFixed(1) : "—"}
            </span>
          </Link>
        ))}
        <p className="board-footnote">
          Probabilities are fair value derived from the moneyline. Featured odds drawn from the
          market desk. Lines are informational, not a recommendation.
        </p>
      </section>
    </>
  );
}

export default Home;