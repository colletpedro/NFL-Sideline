import type { Game } from "../services/types";

type ResultGame = Pick<Game, "homeScore" | "awayScore" | "result" | "homeTeam" | "awayTeam">;

export interface FinalGameResult {
  homeScore: number;
  awayScore: number;
  label: string;
}

function isValidScore(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value >= 0;
}

export function finalGameResult(game: ResultGame): FinalGameResult | null {
  const { homeScore, awayScore, result } = game;
  if (
    !isValidScore(homeScore)
    || !isValidScore(awayScore)
    || typeof result !== "number"
    || !Number.isInteger(result)
    || result !== homeScore - awayScore
  ) {
    return null;
  }

  if (result === 0) {
    return { homeScore, awayScore, label: "Final · Tie" };
  }

  const winner = result > 0 ? game.homeTeam.teamAbbr : game.awayTeam.teamAbbr;
  return {
    homeScore,
    awayScore,
    label: `Final · ${winner} won by ${Math.abs(result)}`,
  };
}
