import type { Game, MarketImplied } from "./types";
import { fairProbability, favoriteOf, mlToImplied, validFairPair, validProbability } from "./types";

export interface RowData {
  game: Game;
  favAbbr: string | null;
  homePct: number | null;
  awayPct: number | null;
  /** "WED" */
  day: string;
  /** "SEP 09" */
  date: string;
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

export function buildRow(game: Game): RowData {
  const probs = gameProbs(game, game.market ?? null);
  const fair = { home: probs.homeFair, away: probs.awayFair };
  const fav = favoriteOf(game, fair);
  return {
    game,
    favAbbr: fav?.teamAbbr ?? null,
    homePct: fair.home,
    awayPct: fair.away,
    day: weekdayOf(game.gameday),
    date: shortDateOf(game.gameday),
  };
}

export interface GameProbs {
  homeFair: number | null;
  awayFair: number | null;
  homeRaw: number | null;
  awayRaw: number | null;
}

/**
 * Fair market probability comes from the valid market snapshot, falling back
 * to proportional vig removal from a valid moneyline pair. Raw includes vig.
 */
export function gameProbs(game: Game, market: MarketImplied | null): GameProbs {
  let homeFair: number | null = null;
  let awayFair: number | null = null;
  if (
    market && validFairPair(market.homeImpliedFair, market.awayImpliedFair)
  ) {
    homeFair = market.homeImpliedFair;
    awayFair = market.awayImpliedFair;
  } else {
    const fair = fairProbability(game.homeMoneyline, game.awayMoneyline);
    homeFair = fair?.home ?? null;
    awayFair = fair?.away ?? null;
  }

  let homeRaw: number | null =
    market?.homeImpliedRaw !== null && market?.homeImpliedRaw !== undefined
      ? market.homeImpliedRaw
      : null;
  let awayRaw: number | null =
    market?.awayImpliedRaw !== null && market?.awayImpliedRaw !== undefined
      ? market.awayImpliedRaw
      : null;
  if (!validProbability(homeRaw) || !validProbability(awayRaw) || homeRaw + awayRaw <= 1) {
    const fair = fairProbability(game.homeMoneyline, game.awayMoneyline);
    homeRaw = fair.home !== null ? mlToImplied(game.homeMoneyline) : null;
    awayRaw = fair.away !== null ? mlToImplied(game.awayMoneyline) : null;
  }
  return { homeFair, awayFair, homeRaw, awayRaw };
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
