import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";
import { buildRow, gameProbs } from "./model";
import { favoriteOf, fairProbability } from "./types";
import type { Game } from "./types";
import GameRow from "../components/GameRow";
import ModelSignal from "../components/ModelSignal";
import MatchupHero from "../components/MatchupHero";
import OverviewPanel from "../components/OverviewPanel";
import MarketComparison from "../components/MarketComparison";
import Home from "../pages/Home";
import SportsHeader from "../components/SportsHeader";
import { Publication } from "./publicationContext";

const team = (abbr: string) => ({ teamAbbr: abbr, teamName: `${abbr} Team`, conference: null, division: null, logoUrl: null });
const game: Game = {
  gameId: "2029_08_AAA_BBB", season: 2029, week: 8, gameType: "REG", gameday: "2029-10-28",
  homeTeam: team("BBB"), awayTeam: team("AAA"), homeScore: null, awayScore: null, result: null,
  homeMoneyline: null, awayMoneyline: null, spreadLine: null, totalLine: null,
  homeSpreadOdds: null, awaySpreadOdds: null, overOdds: null, underOdds: null,
  roof: null, surface: null, divisionGame: null, updatedAt: null, market: null,
};
const render = (node: React.ReactNode) => renderToStaticMarkup(<StaticRouter location="/">{node}</StaticRouter>);

describe("honest market availability", () => {
  it.each([[null, null], [-150, null], [null, 130], [0, 130], [NaN, 130], [Infinity, 130], [200, 200]])(
    "does not infer a favorite from %s / %s", (home, away) => {
      const g = { ...game, homeMoneyline: home, awayMoneyline: away };
      expect(favoriteOf(g)).toBeNull();
      expect(fairProbability(home, away)).toEqual({ home: null, away: null });
      expect(buildRow(g)).toMatchObject({ favAbbr: null, confidence: null, edge: null, favPct: null });
      expect(gameProbs(g, null)).toEqual({ homeModel: null, awayModel: null, homeRaw: null, awayRaw: null });
    },
  );
  it("uses valid fair data and never invents a favorite for a tie", () => {
    const g = { ...game, homeMoneyline: -150, awayMoneyline: 130 };
    expect(favoriteOf(g)?.teamAbbr).toBe("BBB");
    expect(buildRow(g).favPct).toBeGreaterThan(.5);
    expect(favoriteOf({ ...g, homeMoneyline: -110, awayMoneyline: -110 })).toBeNull();
    expect(gameProbs(game, { homeImpliedFair: NaN, awayImpliedFair: .4, homeImpliedRaw: null,
      awayImpliedRaw: null, vigPct: null, computedAt: null }).homeModel).toBeNull();
  });
  it("renders a navigable no-odds row without highlights or fabricated percentages", () => {
    const html = render(<GameRow row={buildRow(game)} />);
    expect(html).toContain(`/game/${game.gameId}`);
    expect(html).toContain("Market unavailable");
    expect(html).toContain("AAA Team");
    expect(html).not.toMatch(/Model pick|confidence|—%|50%|class="gr-pct fav"/i);
    expect(render(<ModelSignal row={buildRow(game)} />)).toBe("");
  });
  it("keeps identity, date and cached analysis visible in a no-odds detail", () => {
    const row = buildRow(game);
    const html = render(<><MatchupHero game={game} awayPct={null} homePct={null} favAbbr={null}
      confidence={null} edge={null} vig={null} weekLabel="Week 08" />
      <OverviewPanel game={game} dogTeam={null} favAbbr={null} favPct={null} dogPct={null}
        confidence={null} edge={null} vig={null} predicao={{ fator_chave: "Cached key factor", veredito: "Cached verdict" }}
        onViewAnalysis={vi.fn()} />
      <MarketComparison game={game} market={null} favAbbr={row.favAbbr} edge={row.edge} /></>);
    expect(html).toContain("AAA Team");
    expect(html).toContain("OCT 28");
    expect(html).toContain("Cached verdict");
    expect(html).toContain("Market unavailable");
    expect(html).not.toMatch(/Model Pick|Biggest Edge|confidence|—%|50%|mu-pct fav|ov-edge|mc-compare/i);
  });
  it("hides the home signal when all games lack probabilities, and uses the context week", () => {
    const html = render(<Publication.Provider value={{ publication: { defaultSeason: 2029, generatedAt: null },
      games: [game], loading: false, error: null, retry: vi.fn(), selectedWeek: 8,
      selectWeek: vi.fn(), setDetailGame: vi.fn() }}><Home /></Publication.Provider>);
    expect(html).toContain("Week 08 Games");
    expect(html).toContain("Market availability");
    expect(html).toContain("2029");
    expect(html).not.toContain("2026");
    expect(html).not.toMatch(/Biggest Edge|favorite in lime|Model Probability|—%/);
    const header = render(<SportsHeader season={2029} week={8} updatedLabel="Updated 1h ago" />);
    expect(header).toContain("2029");
    expect(header).toContain("Week 08");
    expect(header).not.toContain("2026");
  });
});
