import type { Game, MarketImplied, Team } from "./types";
import { fairProbability, favoriteOf, mlToImplied } from "./types";

export type Confidence = "HIGH" | "MEDIUM" | "LOW";

export interface RowData {
  game: Game;
  favTeam: Team;
  dogTeam: Team;
  favAbbr: string;
  dogAbbr: string;
  /** Favorite win probability, 0–1. */
  favPct: number | null;
  /** Dog win probability, 0–1. */
  dogPct: number | null;
  /** Model edge over a coin flip, in percentage points (0–50). */
  edge: number | null;
  confidence: Confidence | null;
  /** "WED" */
  day: string;
  /** "SEP 09" */
  date: string;
  /** "WED SEP 09" */
  dayDate: string;
}

const WEEKDAYS = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"] as const;

export function weekdayOf(iso: string | null | undefined): string {
  if (!iso) return "—";
  return WEEKDAYS[new Date(`${iso}T00:00:00Z`).getUTCDay()];
}

export function shortDateOf(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00Z`)
    .toLocaleDateString("en-US", { timeZone: "UTC", month: "short", day: "2-digit" })
    .toUpperCase()
    .replace(".", "");
}

export function dayDateOf(iso: string | null | undefined): string {
  if (!iso) return "—";
  return `${weekdayOf(iso)} ${shortDateOf(iso)}`;
}

export function confidenceOf(favPct: number | null): Confidence | null {
  if (favPct === null) return null;
  if (favPct >= 0.7) return "HIGH";
  if (favPct >= 0.6) return "MEDIUM";
  return "LOW";
}

/** Model edge over a coin flip, in percentage points (0–50). */
export function edgePts(favPct: number | null): number | null {
  if (favPct === null) return null;
  return (favPct - 0.5) * 100;
}

export function fmtEdge(pts: number | null | undefined): string {
  if (pts === null || pts === undefined || Number.isNaN(pts)) return "—";
  return `${pts >= 0 ? "+" : ""}${pts.toFixed(1)}`;
}

export function buildRow(game: Game): RowData {
  const fav = favoriteOf(game);
  const dog = fav === game.homeTeam ? game.awayTeam : game.homeTeam;
  const fair = fairProbability(game.homeMoneyline, game.awayMoneyline);
  let favPct: number | null = null;
  if (fair !== null && fair.home !== null && fair.away !== null) {
    favPct = fav === game.homeTeam ? fair.home : fair.away;
  }
  const dogPct = favPct !== null ? 1 - favPct : null;
  return {
    game,
    favTeam: fav,
    dogTeam: dog,
    favAbbr: fav.teamAbbr,
    dogAbbr: dog.teamAbbr,
    favPct,
    dogPct,
    edge: edgePts(favPct),
    confidence: confidenceOf(favPct),
    day: weekdayOf(game.gameday),
    date: shortDateOf(game.gameday),
    dayDate: dayDateOf(game.gameday),
  };
}

export interface GameProbs {
  homeModel: number | null;
  awayModel: number | null;
  homeRaw: number | null;
  awayRaw: number | null;
}

/**
 * Model read = vig-free fair value (market snapshot when available,
 * moneyline fair otherwise). Market read = raw implied incl. vig.
 */
export function gameProbs(game: Game, market: MarketImplied | null): GameProbs {
  let homeModel: number | null = null;
  let awayModel: number | null = null;
  if (
    market?.homeImpliedFair !== null &&
    market?.homeImpliedFair !== undefined &&
    market?.awayImpliedFair !== null &&
    market?.awayImpliedFair !== undefined
  ) {
    homeModel = market.homeImpliedFair;
    awayModel = market.awayImpliedFair;
  } else {
    const fair = fairProbability(game.homeMoneyline, game.awayMoneyline);
    homeModel = fair?.home ?? null;
    awayModel = fair?.away ?? null;
  }

  let homeRaw: number | null =
    market?.homeImpliedRaw !== null && market?.homeImpliedRaw !== undefined
      ? market.homeImpliedRaw
      : null;
  let awayRaw: number | null =
    market?.awayImpliedRaw !== null && market?.awayImpliedRaw !== undefined
      ? market.awayImpliedRaw
      : null;
  if (homeRaw === null || awayRaw === null) {
    homeRaw = mlToImplied(game.homeMoneyline);
    awayRaw = mlToImplied(game.awayMoneyline);
  }
  return { homeModel, awayModel, homeRaw, awayRaw };
}

export function formatUpdated(iso: string | null | undefined): string {
  if (!iso) return "Updated —";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "Updated just now";
  if (mins < 60) return `Updated ${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `Updated ${hrs}h ago`;
  return `Updated ${Math.floor(hrs / 24)}d ago`;
}