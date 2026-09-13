import { describe, expect, it, vi } from "vitest";
import { StaticNflDataClient, testing } from "./staticDataClient";
import type { SnapshotManifest, SnapshotSeason } from "./types";

const manifest: SnapshotManifest = {
  schemaVersion: 1,
  generatedAt: "2026-09-10T12:00:00Z",
  defaultSeason: 2026,
  seasons: [2026],
};

const season: SnapshotSeason = {
  schemaVersion: 1,
  season: 2026,
  generatedAt: "2026-09-10T12:00:00Z",
  teams: [
    { teamAbbr: "AAA", teamName: "Away", conference: "A", division: null, logoUrl: null },
    { teamAbbr: "HHH", teamName: "Home", conference: "N", division: null, logoUrl: null },
  ],
  games: [{
    gameId: "2026_01_AAA_HHH", season: 2026, week: 1, gameType: "REG", gameday: "2026-09-10",
    awayTeamAbbr: "AAA", homeTeamAbbr: "HHH", awayScore: null, homeScore: null, result: null,
    spreadLine: -2.5, totalLine: 44.5, awayMoneyline: 120, homeMoneyline: -140,
    homeSpreadOdds: -110, awaySpreadOdds: -110, overOdds: -105, underOdds: -115,
    roof: "outdoors", surface: "grass", divisionGame: false, updatedAt: "2026-09-10T10:00:00Z",
    market: { homeImpliedRaw: .58, awayImpliedRaw: .45, homeImpliedFair: .56, awayImpliedFair: .44, vigPct: .03, computedAt: "2026-09-10T10:00:00Z" },
  }],
  metricsByTeam: {
    AAA: [{ season: 2026, week: 1, teamAbbr: "AAA", offEpaPlay: .1, offEpaPass: .2, offEpaRush: 0, defEpaPass: -.1, defEpaRush: .02, dropbackRate: .6, playsOffense: 60 }],
    HHH: [],
  },
  analysesByGame: {
    "2026_01_AAA_HHH": { gameId: "2026_01_AAA_HHH", analysisType: "matchup", createdAt: "2026-09-10T11:00:00Z", fatorChave: "Key", vantagemTatica: "Edge", alertaVermelho: "Alert", veredito: "Verdict" },
  },
};

function fetcher(overrides: Partial<Record<string, unknown>> = {}) {
  return vi.fn(async (input: RequestInfo | URL) => {
    const path = input.toString();
    const body = overrides[path] ?? (path.endsWith("manifest.json") ? manifest : season);
    if (body instanceof Error) throw body;
    return Response.json(body);
  }) as unknown as typeof fetch;
}

describe("static snapshot client", () => {
  it("takes the default season and publication time from the manifest", async () => {
    const context = { ...manifest, defaultSeason: 2029, seasons: [2029] };
    const client = new StaticNflDataClient(fetcher({ "/data/manifest.json": context }));
    expect(await client.getPublicationContext()).toEqual({ defaultSeason: 2029, generatedAt: manifest.generatedAt });
    expect(() => testing.validateManifest({ ...manifest, defaultSeason: 2029 })).toThrow();
  });

  it("assembles a game without market while preserving its analysis and identity", async () => {
    const withoutMarket = { ...season, games: [{ ...season.games[0], market: null,
      homeMoneyline: null, awayMoneyline: null, spreadLine: null, totalLine: null }] };
    const client = new StaticNflDataClient(fetcher({ "/data/seasons/2026.json": withoutMarket }));
    const detail = await client.getGameDetail(season.games[0].gameId);
    expect(detail?.market).toBeNull();
    expect(detail?.game.homeMoneyline).toBeNull();
    expect(detail?.game.homeTeam.teamName).toBe("Home");
    expect(await client.getAvailableAnalysis(season.games[0].gameId)).not.toBeNull();
  });
  it("accepts a valid manifest and rejects an incompatible schema", () => {
    expect(testing.validateManifest(manifest)).toEqual(manifest);
    expect(() => testing.validateManifest({ ...manifest, schemaVersion: 2 })).toThrow(
      "Snapshot data is unavailable or incompatible."
    );
  });

  it("rejects a missing season", async () => {
    await expect(new StaticNflDataClient(fetcher()).listGames(2025)).rejects.toThrow(
      "Snapshot data is unavailable or incompatible."
    );
  });

  it("assembles GameDetail and supports weekly filtering", async () => {
    const client = new StaticNflDataClient(fetcher());
    const games = await client.listGames(2026);
    expect(games.filter((game) => game.week === 1)).toHaveLength(1);
    const detail = await client.getGameDetail("2026_01_AAA_HHH");
    expect(detail?.game.homeTeam.teamName).toBe("Home");
    expect(detail?.market?.vigPct).toBe(.03);
    expect(detail?.awayMetrics[0].id.week).toBe(1);
  });

  it("returns an existing analysis and null when absent", async () => {
    const client = new StaticNflDataClient(fetcher());
    expect((await client.getAvailableAnalysis("2026_01_AAA_HHH"))?.markdownText).toContain("Verdict");
    expect(await client.getAvailableAnalysis("missing")).toBeNull();
  });

  it("caches manifest and season requests in memory and only performs GET", async () => {
    const mockFetch = fetcher();
    const client = new StaticNflDataClient(mockFetch);
    await client.listGames(2026);
    await client.listGames(2026);
    await client.getGameDetail("2026_01_AAA_HHH");
    expect(mockFetch).toHaveBeenCalledTimes(2);
    for (const call of (mockFetch as unknown as ReturnType<typeof vi.fn>).mock.calls) {
      expect(call[1]).toMatchObject({ method: "GET" });
    }
  });

  it("can retry cleanly after a failed request", async () => {
    const mockFetch = vi.fn()
      .mockRejectedValueOnce(new Error("private detail"))
      .mockResolvedValueOnce(Response.json(manifest))
      .mockResolvedValueOnce(Response.json(season));
    const client = new StaticNflDataClient(mockFetch as typeof fetch);
    await expect(client.listGames(2026)).rejects.toThrow("Snapshot data is unavailable or incompatible.");
    client.clearCache();
    await expect(client.listGames(2026)).resolves.toHaveLength(1);
  });
});
