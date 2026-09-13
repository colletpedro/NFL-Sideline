import axios, { type AxiosInstance } from "axios";
import type { NflDataClient, PublicationContext } from "./dataClient";
import type { AnalysisResponse, Game, GameDetail } from "./types";

const LOCAL_API_ORIGIN = ["http:", "", "localhost:8080"].join("/");
const API_PATH = ["", "api", "v1"].join("/");

export function normalizeApiBaseUrl(value: string): string {
  return value.replace(/\/+$/, "");
}

export function resolveApiBaseUrl(mode: string, explicitBaseUrl?: string): string {
  const configured = explicitBaseUrl?.trim();
  const allowsExplicitBaseUrl = mode === "development" || mode === "test";
  return normalizeApiBaseUrl(
    allowsExplicitBaseUrl && configured ? configured : `${LOCAL_API_ORIGIN}${API_PATH}`
  );
}

export class ApiNflDataClient implements NflDataClient {
  private readonly api: AxiosInstance;

  constructor(baseUrl: string) {
    this.api = axios.create({
      baseURL: baseUrl,
      headers: { "Content-Type": "application/json" },
    });
  }

  async listGames(season: number): Promise<Game[]> {
    const response = await this.api.get<Game[]>("/games", { params: { season } });
    if (!Array.isArray(response.data)) throw new Error("Invalid games response");
    return response.data.map((game: Game & { marketImplied?: Game["market"] }) => ({
      ...game, market: game.marketImplied ?? null,
    }));
  }

  async getPublicationContext(): Promise<PublicationContext> {
    return (await this.api.get<PublicationContext>("/publication")).data;
  }

  async getGameDetail(gameId: string): Promise<GameDetail | null> {
    try {
      return (await this.api.get<GameDetail>(`/games/${encodeURIComponent(gameId)}`)).data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) return null;
      throw error;
    }
  }

  async getAvailableAnalysis(gameId: string): Promise<AnalysisResponse | null> {
    try {
      return (await this.api.get<AnalysisResponse>(
        `/analysis/matchup/${encodeURIComponent(gameId)}`
      )).data;
    } catch (error) {
      if (axios.isAxiosError(error) && error.response?.status === 404) return null;
      throw error;
    }
  }

  clearCache(): void {
    // The local API owns freshness; requests are intentionally not cached here.
  }
}

export type ApiFailureKind = "network" | "http";

export function classifyApiFailure(error: unknown): ApiFailureKind {
  return axios.isAxiosError(error) && !error.response ? "network" : "http";
}
