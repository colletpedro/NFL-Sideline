import { useEffect, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { ChevronLeft } from "lucide-react";
import { dataClient } from "#runtime-client";
import type {
  AnalysisResponse,
  Game,
  GameDetail,
  Predicao,
  TeamWeekMetrics,
} from "../services/types";
import { favoriteOf } from "../services/types";
import {
  confidenceOf,
  dayDateOf,
  edgePts,
  gameProbs,
} from "../services/model";
import MatchupHero from "../components/MatchupHero";
import TabNav from "../components/TabNav";
import type { TabKey } from "../components/TabNav";
import OverviewPanel from "../components/OverviewPanel";
import AnalysisSections from "../components/AnalysisSections";
import MarketComparison from "../components/MarketComparison";
import TacticalComparison from "../components/TacticalComparison";
import { usePublication } from "../services/publicationContext";

/** Metrics for the game week; falls back to the latest recorded week. */
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

/** Parse the predictive JSON payload; null when not valid JSON. */
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

function MatchupDashboard() {
  const { setDetailGame } = usePublication();
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<GameDetail | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [weekGames, setWeekGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [loadAttempt, setLoadAttempt] = useState(0);
  const [tab, setTab] = useState<TabKey>("overview");
  const tabRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!id) return;

    let cancelled = false;
    setLoading(true);
    setAnalysisLoading(true);
    setError(null);
    setDetail(null);
    setAnalysis(null);
    setWeekGames([]);
    setTab("overview");

    Promise.all([
      dataClient.getGameDetail(id),
      dataClient.getAvailableAnalysis(id).catch(() => null),
    ])
      .then(async ([loadedDetail, loadedAnalysis]) => {
        if (!loadedDetail) {
          if (!cancelled) setError("Game not found.");
          return;
        }
        const seasonGames = await dataClient.listGames(loadedDetail.game.season);
        if (!cancelled) {
          setDetail(loadedDetail);
          setDetailGame(loadedDetail.game);
          setAnalysis(loadedAnalysis);
          setWeekGames(seasonGames
            .filter((game) => game.week === loadedDetail.game.week)
            .sort((a, b) => (a.gameday ?? "").localeCompare(b.gameday ?? "") || a.gameId.localeCompare(b.gameId)));
        }
      })
      .catch(() => {
        if (!cancelled) setError("This game could not be loaded.");
      })
      .finally(() => {
        if (!cancelled) {
          setLoading(false);
          setAnalysisLoading(false);
        }
      });

    return () => {
      cancelled = true;
      setDetailGame(null);
    };
  }, [id, loadAttempt, setDetailGame]);

  const goToAnalysis = () => {
    setTab("analysis");
    tabRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  useEffect(() => {
    const body = document.body;
    body.classList.toggle("cta-active", tab !== "analysis");
    return () => body.classList.remove("cta-active");
  }, [tab]);

  if (loading) {
    return <div className="page-state">Loading the matchup…</div>;
  }

  if (error || !detail) {
    return (
      <div className="page-state page-state-error" role="alert">
        <p>{error ?? "Game not found."}</p>
        <button
          className="page-state-retry"
          type="button"
          onClick={() => {
            dataClient.clearCache();
            setLoadAttempt((attempt) => attempt + 1);
          }}
        >
          Retry
        </button>
      </div>
    );
  }

  const { game, market } = detail;
  const predicao = parsePredicao(analysis?.markdownText);
  const probs = gameProbs(game, market);
  const favorite = favoriteOf(game, { home: probs.homeModel, away: probs.awayModel });
  const favAbbr = favorite?.teamAbbr ?? null;
  const dogTeam = favorite ? (favorite === game.homeTeam ? game.awayTeam : game.homeTeam) : null;
  const awayPct = probs.awayModel;
  const homePct = probs.homeModel;
  const favPct = favorite ? (favAbbr === game.homeTeam.teamAbbr ? homePct : awayPct) : null;
  const dogPct = favPct !== null ? 1 - favPct : null;
  const confidence = confidenceOf(favPct);
  const edge = edgePts(favPct);
  const vig = market?.vigPct ?? null;

  const homeMetric = metricForWeek(detail.homeMetrics, game.week);
  const awayMetric = metricForWeek(detail.awayMetrics, game.week);

  const gameNo = weekGames.findIndex((g) => g.gameId === game.gameId) + 1;
  const weekLabel = `Week ${String(game.week).padStart(2, "0")}`;
  const position = `${weekLabel} / Game ${String(gameNo).padStart(2, "0")}`;

  return (
    <article>
      <div className="mu-crumb">
        <Link to="/">
          <ChevronLeft size={14} strokeWidth={2.5} aria-hidden="true" />
          All Games
        </Link>
        <span className="pos">{position}</span>
      </div>

      <MatchupHero
        game={game}
        awayPct={awayPct}
        homePct={homePct}
        favAbbr={favAbbr}
        confidence={confidence}
        edge={edge}
        vig={vig}
        weekLabel={weekLabel}
      />

      <div ref={tabRef}>
        <TabNav active={tab} onChange={setTab} />
      </div>

      <div className="tabpanel">
        {tab === "overview" && (
          <OverviewPanel
            game={game}
            dogTeam={dogTeam}
            favAbbr={favAbbr}
            favPct={favPct}
            dogPct={dogPct}
            confidence={confidence}
            edge={edge}
            vig={vig}
            predicao={predicao}
            analysisLoading={analysisLoading}
            onViewAnalysis={goToAnalysis}
          />
        )}
        {tab === "analysis" && <AnalysisSections predicao={predicao} analysisLoading={analysisLoading} />}
        {tab === "market" && (
          <MarketComparison game={game} market={market} favAbbr={favAbbr} edge={edge} />
        )}
        {tab === "matchup" && (
          <TacticalComparison
            awayTeam={game.awayTeam}
            homeTeam={game.homeTeam}
            awayMetric={awayMetric}
            homeMetric={homeMetric}
            week={game.week}
          />
        )}
      </div>

      <div className={`mobile-cta ${tab !== "analysis" && predicao ? "show" : ""}`}>
        <button onClick={goToAnalysis}>View Analysis</button>
      </div>

      <p className="mu-footnote">
        {dayDateOf(game.gameday)} · {weekLabel} · {homePct !== null
          ? "Probabilities are vig-free fair value derived from the market."
          : "Market probabilities are unavailable."} Lines are informational, not a recommendation.
      </p>
    </article>
  );
}

export default MatchupDashboard;
