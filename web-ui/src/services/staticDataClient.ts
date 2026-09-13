import { NflDataError, type NflDataClient } from "./dataClient";
import type {
  AnalysisResponse,
  Game,
  GameDetail,
  SnapshotAnalysis,
  SnapshotGame,
  SnapshotManifest,
  SnapshotMetric,
  SnapshotSeason,
  Team,
} from "./types";

const SCHEMA_VERSION = 1;

export class StaticNflDataClient implements NflDataClient {
  private manifestPromise: Promise<SnapshotManifest> | null = null;
  private readonly seasons = new Map<number, Promise<SnapshotSeason>>();

  constructor(private readonly fetchImpl: typeof fetch) {}

  async getPublicationContext() {
    const { defaultSeason, generatedAt } = await this.loadManifest();
    return { defaultSeason, generatedAt };
  }

  async listGames(season: number): Promise<Game[]> {
    const snapshot = await this.loadSeason(season);
    return hydrateGames(snapshot);
  }

  async getGameDetail(gameId: string): Promise<GameDetail | null> {
    const found = await this.findGame(gameId);
    if (!found) return null;
    const { snapshot, game } = found;
    const teams = teamIndex(snapshot.teams);
    const hydrated = hydrateGame(game, teams);
    return {
      game: hydrated,
      market: game.market,
      homeMetrics: hydrateMetrics(snapshot.metricsByTeam[game.homeTeamAbbr] ?? []),
      awayMetrics: hydrateMetrics(snapshot.metricsByTeam[game.awayTeamAbbr] ?? []),
    };
  }

  async getAvailableAnalysis(gameId: string): Promise<AnalysisResponse | null> {
    const found = await this.findGame(gameId);
    if (!found) return null;
    const analysis = found.snapshot.analysesByGame[gameId];
    return analysis ? toAnalysisResponse(analysis) : null;
  }

  clearCache(): void {
    this.manifestPromise = null;
    this.seasons.clear();
  }

  private loadManifest(): Promise<SnapshotManifest> {
    if (!this.manifestPromise) {
      this.manifestPromise = this.fetchJson("/data/manifest.json")
        .then(validateManifest)
        .catch(() => {
          this.manifestPromise = null;
          throw sanitized();
        });
    }
    return this.manifestPromise;
  }

  private async loadSeason(season: number): Promise<SnapshotSeason> {
    const manifest = await this.loadManifest();
    if (!manifest.seasons.includes(season)) throw new NflDataError();
    let request = this.seasons.get(season);
    if (!request) {
      request = this.fetchJson(`/data/seasons/${season}.json`)
        .then((value) => validateSeason(value, season))
        .catch(() => {
          this.seasons.delete(season);
          throw sanitized();
        });
      this.seasons.set(season, request);
    }
    return request;
  }

  private async findGame(gameId: string): Promise<{ snapshot: SnapshotSeason; game: SnapshotGame } | null> {
    const manifest = await this.loadManifest();
    const orderedSeasons = [manifest.defaultSeason, ...manifest.seasons.filter(
      (season) => season !== manifest.defaultSeason
    )];
    for (const season of orderedSeasons) {
      const snapshot = await this.loadSeason(season);
      const game = snapshot.games.find((candidate) => candidate.gameId === gameId);
      if (game) return { snapshot, game };
    }
    return null;
  }

  private async fetchJson(path: string): Promise<unknown> {
    const response = await this.fetchImpl(path, { method: "GET", credentials: "same-origin" });
    if (!response.ok) throw new NflDataError();
    return response.json();
  }
}

function validateManifest(value: unknown): SnapshotManifest {
  if (!isRecord(value)
      || value.schemaVersion !== SCHEMA_VERSION
      || typeof value.defaultSeason !== "number"
      || !Number.isInteger(value.defaultSeason)
      || typeof value.generatedAt !== "string"
      || !Number.isFinite(Date.parse(value.generatedAt))
      || !Array.isArray(value.seasons)
      || !value.seasons.every((season) => typeof season === "number" && Number.isInteger(season))
      || !value.seasons.includes(value.defaultSeason)) {
    throw new NflDataError();
  }
  return value as unknown as SnapshotManifest;
}

function validateSeason(value: unknown, expectedSeason: number): SnapshotSeason {
  if (!isRecord(value)
      || value.schemaVersion !== SCHEMA_VERSION
      || value.season !== expectedSeason
      || !Array.isArray(value.teams)
      || !Array.isArray(value.games)
      || !isRecord(value.metricsByTeam)
      || !isRecord(value.analysesByGame)) {
    throw new NflDataError();
  }
  const snapshot = value as unknown as SnapshotSeason;
  if (!snapshot.teams.every(validTeam)
      || !snapshot.games.every(validGame)
      || !Object.values(snapshot.metricsByTeam).every((metrics) => Array.isArray(metrics)
        && metrics.every((metric) => isRecord(metric)
          && typeof metric.season === "number"
          && typeof metric.week === "number"
          && typeof metric.teamAbbr === "string"))
      || !Object.values(snapshot.analysesByGame).every(validAnalysis)) {
    throw new NflDataError();
  }
  return snapshot;
}

function validAnalysis(value: unknown): value is SnapshotAnalysis {
  return isRecord(value)
    && typeof value.gameId === "string"
    && value.analysisType === "matchup"
    && typeof value.createdAt === "string"
    && nonEmpty(value.fatorChave)
    && nonEmpty(value.vantagemTatica)
    && nonEmpty(value.alertaVermelho)
    && nonEmpty(value.veredito);
}

function nonEmpty(value: unknown): value is string {
  return typeof value === "string" && value.trim().length > 0;
}

function validTeam(value: unknown): value is Team {
  return isRecord(value) && typeof value.teamAbbr === "string" && typeof value.teamName === "string";
}

function validGame(value: unknown): value is SnapshotGame {
  return isRecord(value)
    && typeof value.gameId === "string"
    && typeof value.season === "number"
    && typeof value.week === "number"
    && (typeof value.gameday === "string" || value.gameday === null)
    && typeof value.homeTeamAbbr === "string"
    && typeof value.awayTeamAbbr === "string";
}

function hydrateGames(snapshot: SnapshotSeason): Game[] {
  const teams = teamIndex(snapshot.teams);
  return snapshot.games.map((game) => hydrateGame(game, teams));
}

function teamIndex(teams: Team[]): Map<string, Team> {
  return new Map(teams.map((team) => [team.teamAbbr, team]));
}

function hydrateGame(game: SnapshotGame, teams: Map<string, Team>): Game {
  const homeTeam = teams.get(game.homeTeamAbbr);
  const awayTeam = teams.get(game.awayTeamAbbr);
  if (!homeTeam || !awayTeam) throw new NflDataError();
  return { ...game, homeTeam, awayTeam };
}

function toAnalysisResponse(analysis: SnapshotAnalysis): AnalysisResponse {
  return {
    gameId: analysis.gameId,
    markdownText: JSON.stringify({
      fator_chave: analysis.fatorChave,
      vantagem_tatica: analysis.vantagemTatica,
      alerta_vermelho: analysis.alertaVermelho,
      veredito: analysis.veredito,
    }),
    fromCache: true,
  };
}

function hydrateMetrics(metrics: SnapshotMetric[]) {
  return metrics.map((metric) => ({
    id: { season: metric.season, week: metric.week, teamAbbr: metric.teamAbbr },
    offEpaPlay: metric.offEpaPlay,
    offEpaPass: metric.offEpaPass,
    offEpaRush: metric.offEpaRush,
    defEpaPass: metric.defEpaPass,
    defEpaRush: metric.defEpaRush,
    dropbackRate: metric.dropbackRate,
    playsOffense: metric.playsOffense,
  }));
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function sanitized(): NflDataError {
  return new NflDataError();
}

export const testing = { validateManifest, validateSeason, hydrateGames };
