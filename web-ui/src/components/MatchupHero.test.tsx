import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import type { Confidence } from "../services/model";
import type { Game } from "../services/types";
import MatchupHero from "./MatchupHero";

const team = (teamAbbr: string) => ({
  teamAbbr,
  teamName: `${teamAbbr} Team`,
  conference: null,
  division: null,
  logoUrl: null,
});

const game: Game = {
  gameId: "2026_01_NE_SEA",
  season: 2026,
  week: 1,
  gameType: "REG",
  gameday: "2026-09-09",
  awayTeam: team("NE"),
  homeTeam: team("SEA"),
  awayScore: null,
  homeScore: null,
  result: null,
  awayMoneyline: 140,
  homeMoneyline: -166,
  spreadLine: 3,
  totalLine: 44.5,
  homeSpreadOdds: null,
  awaySpreadOdds: null,
  overOdds: null,
  underOdds: null,
  roof: null,
  surface: null,
  divisionGame: null,
  updatedAt: null,
  market: null,
};

interface HeroMarket {
  awayPct: number | null;
  homePct: number | null;
  favAbbr: string | null;
  confidence: Confidence | null;
  edge: number | null;
  vig: number | null;
}

const market: HeroMarket = {
  awayPct: 0.4,
  homePct: 0.6,
  favAbbr: "SEA",
  confidence: "MEDIUM",
  edge: 10,
  vig: 0.04,
};

const noMarket: HeroMarket = {
  awayPct: null,
  homePct: null,
  favAbbr: null,
  confidence: null,
  edge: null,
  vig: null,
};

function renderHero(gameOverrides: Partial<Game> = {}, heroMarket: HeroMarket = market): string {
  return renderToStaticMarkup(
    <MatchupHero
      game={{ ...game, ...gameOverrides }}
      {...heroMarket}
      weekLabel="Week 01"
    />,
  );
}

describe("MatchupHero score presentation", () => {
  it("completed home win shows scores and home winner", () => {
    const html = renderHero({ awayScore: 10, homeScore: 13, result: 3 });

    expect(html).toContain('aria-label="NE score 10">10</span>');
    expect(html).toContain('aria-label="SEA score 13">13</span>');
    expect(html).toContain("Final · SEA won by 3");
    expect(html).not.toContain('aria-label="NE win probability');
    expect(html).not.toContain('aria-label="SEA win probability');
    expect(html).toContain("NE 40%");
    expect(html).toContain("SEA 60%");
  });

  it("completed away win shows scores and away winner", () => {
    const html = renderHero({
      gameId: "2026_01_SF_LA",
      awayTeam: team("SF"),
      homeTeam: team("LA"),
      awayScore: 27,
      homeScore: 7,
      result: -20,
    });

    expect(html).toContain('aria-label="SF score 27">27</span>');
    expect(html).toContain('aria-label="LA score 7">7</span>');
    expect(html).toContain("Final · SF won by 20");
    expect(html).not.toContain("won by -20");
  });

  it("completed game without market still shows scores", () => {
    const html = renderHero({ awayScore: 10, homeScore: 13, result: 3 }, noMarket);

    expect(html).toContain('aria-label="NE score 10">10</span>');
    expect(html).toContain('aria-label="SEA score 13">13</span>');
    expect(html).toContain("Final · SEA won by 3");
    expect(html).not.toMatch(/Market favorite|confidence|Market edge/);
  });

  it("completed tie shows final tie", () => {
    const html = renderHero({ awayScore: 17, homeScore: 17, result: 0 });

    expect(html).toContain('aria-label="NE score 17">17</span>');
    expect(html).toContain('aria-label="SEA score 17">17</span>');
    expect(html).toContain("Final · Tie");
    expect(html).not.toContain("won by");
  });

  it("future game with market keeps probability presentation", () => {
    const html = renderHero();

    expect(html).toContain('aria-label="NE win probability 40.0 percent">40.0%</span>');
    expect(html).toContain('aria-label="SEA win probability 60.0 percent">60.0%</span>');
    expect(html).toContain("Market favorite: SEA");
    expect(html).not.toContain("Final");
  });

  it("future game without market keeps neutral presentation", () => {
    const html = renderHero({}, noMarket);

    expect(html).toContain('aria-label="NE primary value unavailable">—</span>');
    expect(html).toContain('aria-label="SEA primary value unavailable">—</span>');
    expect(html).toContain("Market unavailable");
    expect(html).not.toMatch(/Final|Market favorite|confidence|Market edge/);
  });

  it("partial score trio is not final", () => {
    const html = renderHero({ awayScore: 10, homeScore: null, result: null });

    expect(html).toContain('aria-label="NE primary value unavailable">—</span>');
    expect(html).toContain('aria-label="SEA primary value unavailable">—</span>');
    expect(html).not.toMatch(/Final|score 10|won by/);
    expect(html).not.toContain('aria-label="SEA win probability');
  });

  it("inconsistent result is not final", () => {
    const html = renderHero({ awayScore: 10, homeScore: 13, result: 4 }, noMarket);

    expect(html).toContain('aria-label="NE primary value unavailable">—</span>');
    expect(html).toContain('aria-label="SEA primary value unavailable">—</span>');
    expect(html).not.toMatch(/Final|won by/);
  });
});
