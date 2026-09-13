import type { AnalysisResponse, Game, GameDetail } from "./types";

export interface NflDataClient {
  getPublicationContext(): Promise<PublicationContext>;
  listGames(season: number): Promise<Game[]>;
  getGameDetail(gameId: string): Promise<GameDetail | null>;
  getAvailableAnalysis(gameId: string): Promise<AnalysisResponse | null>;
  clearCache(): void;
}

export interface PublicationContext {
  defaultSeason: number;
  /** Snapshot generation in static mode; latest data update in REST mode. */
  generatedAt: string | null;
}

export class NflDataError extends Error {
  constructor() {
    super("Snapshot data is unavailable or incompatible.");
    this.name = "NflDataError";
  }
}
