import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import { api } from "../services/api";
import ModelReadout from "../components/ModelReadout";
import ProbabilitySplit from "../components/ProbabilitySplit";
import type {
  AnalysisResponse,
  Game,
  GameDetail,
  Predicao,
  TeamWeekMetrics,
} from "../services/types";
import {
  fairProbability,
  favoriteOf,
  fmtDateLong,
  fmtLine,
  fmtPct,
  fmtNum,
} from "../services/types";

/**
 * Métrica do time para a semana do jogo. Prefere a semana exata do confronto;
 * se ainda não houver dado (jogo futuro), cai para a última semana jogada
 * (week <= alvo) e, por fim, para o último registro da série.
 */
function metricForWeek(
  series: TeamWeekMetrics[] | undefined,
  week: number
): TeamWeekMetrics | null {
  if (!series || series.length === 0) return null;
  const exact = series.find((m) => m.id.week === week);
  if (exact) return exact;
  let latestBefore: TeamWeekMetrics | null = null;
  for (const m of series) {
    if (m.id.week <= week) latestBefore = m;
  }
  return latestBefore ?? series[series.length - 1];
}

/** Faz o parse do JSON preditivo; devolve null se não for JSON válido. */
function parsePredicao(markdownText: string | undefined): Predicao | null {
  if (!markdownText) return null;
  try {
    const parsed: unknown = JSON.parse(markdownText);
    if (typeof parsed !== "object" || parsed === null) return null;
    return parsed as Predicao;
  } catch {
    return null;
  }
}

/** Abertura jornalística composta apenas de dados estruturados. */
function buildLead(game: Game, favAbbr: string, favPct: number | null): string {
  const fav = favAbbr === game.homeTeam.teamAbbr ? game.homeTeam : game.awayTeam;
  const dog = fav === game.homeTeam ? game.awayTeam : game.homeTeam;
  const parts: string[] = [
    `${fav.teamName} travel to ${dog.teamName} in Week ${game.week} of the ${game.season} season.`,
  ];
  if (favPct !== null) {
    parts.push(
      `The model opens with ${fav.teamName} at ${(favPct * 100).toFixed(1)} percent.`
    );
  }
  const line: string[] = [];
  if (game.spreadLine !== null && game.spreadLine !== undefined) {
    line.push(`a line of ${fmtLine(game.spreadLine)}`);
  }
  if (game.totalLine !== null && game.totalLine !== undefined) {
    line.push(`a total of ${game.totalLine.toFixed(1)}`);
  }
  if (line.length > 0) {
    parts.push(`The board carries ${line.join(" and ")}.`);
  }
  return parts.join(" ");
}

function MatchupDashboard() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<GameDetail | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [weekGames, setWeekGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      api.get<GameDetail>(`/games/${id}`),
      api.post<AnalysisResponse>("/analysis/matchup", {
        gameId: id,
        analysisType: "matchup",
      }),
    ])
      .then(([detailResponse, analysisResponse]) => {
        if (cancelled) return;
        setDetail(detailResponse.data);
        setAnalysis(analysisResponse.data);
      })
      .catch((err) => {
        if (cancelled) return;
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          setError("Game not found.");
        } else if (axios.isAxiosError(err) && err.response?.status === 503) {
          setError("The model could not produce this edition.");
        } else {
          setError("The edition could not be loaded.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  /** Numeração editorial do jogo dentro da semana (WEEK 01 / GAME 03). */
  useEffect(() => {
    if (!detail) return;
    let cancelled = false;
    api
      .get<Game[]>("/games", { params: { season: detail.game.season, week: detail.game.week } })
      .then((r) => {
        if (!cancelled) setWeekGames(r.data);
      })
      .catch(() => {
        /* numeração é opcional */
      });
    return () => {
      cancelled = true;
    };
  }, [detail?.game.season, detail?.game.week]);

  if (loading) {
    return <div className="page-state">Composing the edition…</div>;
  }

  if (error || !detail) {
    return <div className="page-state">{error ?? "Game not found."}</div>;
  }

  const { game, market } = detail;
  const predicao = parsePredicao(analysis?.markdownText);
  const favorite = favoriteOf(game);
  const favAbbr = favorite.teamAbbr;

  const marketFair =
    market?.homeImpliedFair !== null && market?.homeImpliedFair !== undefined &&
    market?.awayImpliedFair !== null && market?.awayImpliedFair !== undefined
      ? { home: market.homeImpliedFair, away: market.awayImpliedFair }
      : null;
  const mlFair = fairProbability(game.homeMoneyline, game.awayMoneyline);
  const homePct =
    marketFair ? marketFair.home : mlFair && mlFair.home !== null ? mlFair.home : null;
  const awayPct =
    marketFair ? marketFair.away : mlFair && mlFair.away !== null ? mlFair.away : null;
  const favPct = favAbbr === game.homeTeam.teamAbbr ? homePct : awayPct;

  const homeMetric = metricForWeek(detail.homeMetrics, game.week);
  const awayMetric = metricForWeek(detail.awayMetrics, game.week);

  const gameNo = weekGames.findIndex((g) => g.gameId === game.gameId) + 1;
  const kicker = `Week ${String(game.week).padStart(2, "0")}${
    gameNo > 0 ? ` / Game ${String(gameNo).padStart(2, "0")}` : ""
  }`;

  return (
    <article>
      <header className="hero">
        <p className="hero-kicker">{kicker} — {fmtDateLong(game.gameday)}</p>
        <h1 className="hero-matchup">
          {game.awayTeam.teamName} <span className="at">@</span> {game.homeTeam.teamName}
        </h1>

        <div className="hero-stats">
          <div className="hero-stat">
            <span className="label">Away — {game.awayTeam.teamAbbr}</span>
            <span className={`value ${favAbbr === game.awayTeam.teamAbbr ? "fav" : ""}`}>
              {fmtPct(awayPct)}
            </span>
          </div>
          <div className="hero-stat">
            <span className="label">Home — {game.homeTeam.teamAbbr}</span>
            <span className={`value ${favAbbr === game.homeTeam.teamAbbr ? "fav" : ""}`}>
              {fmtPct(homePct)}
            </span>
          </div>
          <div className="hero-stat">
            <span className="label">Spread</span>
            <span className="value">
              {fmtLine(game.spreadLine)} <small>{favAbbr}</small>
            </span>
          </div>
          <div className="hero-stat">
            <span className="label">Total</span>
            <span className="value">{fmtNum(game.totalLine, 1)}</span>
          </div>
        </div>

        {favPct !== null && (
          <div className="hero-favorite">
            <span className="flag" aria-hidden="true" />
            <span className="text">Model favorite — {favAbbr} at {(favPct * 100).toFixed(1)}%</span>
          </div>
        )}
      </header>

      <p className="lead">
        <span className="lead-mono">The editorial desk</span>
        {buildLead(game, favAbbr, favPct)}
      </p>

      <section className="case">
        <div className="case-seq">
          <section className="case-section">
            <span className="case-no">01</span>
            <h2 className="case-head">The Matchup</h2>
            <p className="case-body">{predicao?.fator_chave ?? "The desk's analysis is not available for this game."}</p>
          </section>

          <section className="case-section">
            <span className="case-no">02</span>
            <h2 className="case-head">The Advantage</h2>
            <p className="case-body">{predicao?.vantagem_tatica ?? "The desk's analysis is not available for this game."}</p>
          </section>

          <section className="red-flag">
            <span className="case-no">03</span>
            <h2 className="case-head">Red Flag</h2>
            <p className="case-body">{predicao?.alerta_vermelho ?? "The desk's analysis is not available for this game."}</p>
          </section>

          <section className="case-section case-verdict">
            <span className="case-no">04</span>
            <h2 className="case-head">The Verdict</h2>
            <p className="case-body">{predicao?.veredito ?? "The desk's analysis is not available for this game."}</p>
          </section>
        </div>

        <ModelReadout
          game={game}
          market={market}
          homePct={homePct}
          awayPct={awayPct}
          favoriteAbbr={favAbbr}
          fromCache={analysis?.fromCache ?? false}
        />
      </section>

      <section className="ledger">
        <div className="ledger-head">
          <h2 className="ledger-title">Weekly Ledger</h2>
          <span className="ledger-week">Week {String(game.week).padStart(2, "0")} form</span>
        </div>
        {homeMetric || awayMetric ? (
          <div className="ledger-cols">
            {[
              { team: game.homeTeam, metric: homeMetric },
              { team: game.awayTeam, metric: awayMetric },
            ].map(({ team, metric }) => (
              <div key={team.teamAbbr} className="ledger-team">
                <p className="ledger-team-name">{team.teamName}</p>
                {metric ? (
                  <>
                    <div className="ledger-row">
                      <span className="k">EPA / Play</span>
                      <span className="v">{fmtNum(metric.offEpaPlay, 3)}</span>
                    </div>
                    <div className="ledger-row">
                      <span className="k">Air EPA</span>
                      <span className="v">{fmtNum(metric.offEpaPass, 3)}</span>
                    </div>
                    <div className="ledger-row">
                      <span className="k">Ground EPA</span>
                      <span className="v">{fmtNum(metric.offEpaRush, 3)}</span>
                    </div>
                    <div className="ledger-row">
                      <span className="k">Plays</span>
                      <span className="v">{metric.playsOffense ?? "—"}</span>
                    </div>
                    {metric.dropbackRate !== null && metric.dropbackRate !== undefined && (
                      <div className="ledger-split">
                        <ProbabilitySplit
                          left={{ abbr: "Pass", pct: metric.dropbackRate * 100 }}
                          right={{ abbr: "Run", pct: (1 - metric.dropbackRate) * 100 }}
                          favSide={metric.dropbackRate >= 0.5 ? "left" : "right"}
                        />
                      </div>
                    )}
                  </>
                ) : (
                  <p className="ledger-note">No weekly ledger recorded for this team.</p>
                )}
              </div>
            ))}
          </div>
        ) : (
          <p className="ledger-note">
            The play-by-play ledger opens with the season — no weeks recorded yet.
          </p>
        )}
      </section>
    </article>
  );
}

export default MatchupDashboard;