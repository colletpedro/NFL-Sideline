export interface Team {
  teamAbbr: string;
  teamName: string;
  conference: string | null;
  division: string | null;
  logoUrl: string | null;
}

export interface Game {
  gameId: string;
  season: number;
  week: number;
  gameType: string;
  gameday: string | null;
  homeTeam: Team;
  awayTeam: Team;
  homeScore: number | null;
  awayScore: number | null;
  result: number | null;
  spreadLine: number | null;
  totalLine: number | null;
  homeMoneyline: number | null;
  awayMoneyline: number | null;
  homeSpreadOdds: number | null;
  awaySpreadOdds: number | null;
  overOdds: number | null;
  underOdds: number | null;
  roof: string | null;
  surface: string | null;
  divisionGame: boolean | null;
  updatedAt: string | null;
  market?: MarketImplied | null;
}

export interface MarketImplied {
  homeImpliedRaw: number | null;
  awayImpliedRaw: number | null;
  homeImpliedFair: number | null;
  awayImpliedFair: number | null;
  vigPct: number | null;
  computedAt: string | null;
}

export interface TeamWeekMetrics {
  id: { season: number; week: number; teamAbbr: string };
  offEpaPlay: number | null;
  offEpaPass: number | null;
  offEpaRush: number | null;
  defEpaPass: number | null;
  defEpaRush: number | null;
  dropbackRate: number | null;
  playsOffense: number | null;
}

export interface GameDetail {
  game: Game;
  market: MarketImplied | null;
  homeMetrics: TeamWeekMetrics[];
  awayMetrics: TeamWeekMetrics[];
}

export interface AnalysisResponse {
  gameId: string;
  markdownText: string;
  fromCache: boolean;
}

export interface SnapshotManifest {
  schemaVersion: number;
  generatedAt: string;
  defaultSeason: number;
  seasons: number[];
}

export interface SnapshotGame {
  gameId: string;
  season: number;
  week: number;
  gameType: string;
  gameday: string | null;
  homeTeamAbbr: string;
  awayTeamAbbr: string;
  homeScore: number | null;
  awayScore: number | null;
  result: number | null;
  spreadLine: number | null;
  totalLine: number | null;
  homeMoneyline: number | null;
  awayMoneyline: number | null;
  homeSpreadOdds: number | null;
  awaySpreadOdds: number | null;
  overOdds: number | null;
  underOdds: number | null;
  roof: string | null;
  surface: string | null;
  divisionGame: boolean | null;
  updatedAt: string | null;
  market: MarketImplied | null;
}

export interface SnapshotAnalysis {
  gameId: string;
  analysisType: "matchup";
  createdAt: string;
  fatorChave: string;
  vantagemTatica: string;
  alertaVermelho: string;
  veredito: string;
}

export interface SnapshotMetric {
  season: number;
  week: number;
  teamAbbr: string;
  offEpaPlay: number | null;
  offEpaPass: number | null;
  offEpaRush: number | null;
  defEpaPass: number | null;
  defEpaRush: number | null;
  dropbackRate: number | null;
  playsOffense: number | null;
}

export interface SnapshotSeason {
  schemaVersion: number;
  season: number;
  generatedAt: string;
  teams: Team[];
  games: SnapshotGame[];
  metricsByTeam: Record<string, SnapshotMetric[]>;
  analysesByGame: Record<string, SnapshotAnalysis>;
}

/** Objeto preditivo estruturado exigido do LLM (contrato Fase 9). */
export interface Predicao {
  fator_chave?: string;
  vantagem_tatica?: string;
  alerta_vermelho?: string;
  veredito?: string;
}

/** Probabilidade implícita bruta de uma moneyline americana (spec §7.1). */
export function mlToImplied(ml: number | null | undefined): number | null {
  if (ml === null || ml === undefined || !Number.isFinite(ml) || !Number.isInteger(ml) || ml === 0) return null;
  return ml < 0 ? Math.abs(ml) / (Math.abs(ml) + 100) : 100 / (ml + 100);
}

/** Probabilidade justa (sem vig) a partir das duas moneylines. */
export function fairProbability(
  homeMl: number | null | undefined,
  awayMl: number | null | undefined
): { home: number | null; away: number | null } {
  const h = mlToImplied(homeMl);
  const a = mlToImplied(awayMl);
  if (h === null || a === null) return { home: null, away: null };
  const sum = h + a;
  if (sum <= 1) return { home: null, away: null };
  return { home: h / sum, away: a / sum };
}

export function validProbability(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value) && value > 0 && value < 1;
}

export function validFairPair(home: unknown, away: unknown): boolean {
  return validProbability(home) && validProbability(away) && Math.abs(home + away - 1) < 1e-9;
}

/** Sem par fair válido (ou em empate), não existe favorito. */
export function favoriteOf(
  game: Pick<Game, "homeTeam" | "awayTeam" | "homeMoneyline" | "awayMoneyline">,
  fair = fairProbability(game.homeMoneyline, game.awayMoneyline),
): Team | null {
  if (!validFairPair(fair.home, fair.away) || fair.home === fair.away) return null;
  return fair.home! > fair.away! ? game.homeTeam : game.awayTeam;
}

export function fmtPct(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${(value * 100).toFixed(digits)}%`;
}

export function fmtNum(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(digits);
}

/** "13 September 2026" */
export function fmtDateLong(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00Z`).toLocaleDateString("en-US", {
    timeZone: "UTC",
    day: "numeric",
    month: "long",
    year: "numeric",
  });
}

/** "SEP 13" */
export function fmtDateShort(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(`${iso}T00:00:00Z`)
    .toLocaleDateString("en-US", { timeZone: "UTC", day: "2-digit", month: "short" })
    .toUpperCase()
    .replace(".", "");
}

/** Linha de spread com sinal explícito: "+3.5" / "-1.5". */
export function fmtLine(spread: number | null | undefined): string {
  if (spread === null || spread === undefined || Number.isNaN(spread)) return "—";
  return `${spread > 0 ? "+" : ""}${spread.toFixed(1)}`;
}

export function fmtTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleTimeString("en-US", {
    timeZone: "UTC",
    hour: "2-digit",
    minute: "2-digit",
  });
}
