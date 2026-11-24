import { describe, expect, it, vi } from "vitest";
import { renderToStaticMarkup } from "react-dom/server";
import { StaticRouter } from "react-router-dom/server";
import { buildRow, gameProbs } from "./market";
import { favoriteOf, fairProbability } from "./types";
import type { Game } from "./types";
import GameRow from "../components/GameRow";
import MatchupHero from "../components/MatchupHero";
import OverviewPanel from "../components/OverviewPanel";
import MarketComparison from "../components/MarketComparison";
import Home from "../pages/Home";
import SportsHeader from "../components/SportsHeader";
import TacticalComparison from "../components/TacticalComparison";
import AnalysisSections from "../components/AnalysisSections";
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
      expect(buildRow(g)).toMatchObject({ favAbbr: null, homePct: null, awayPct: null });
      expect(gameProbs(g, null)).toEqual({ homeFair: null, awayFair: null, homeRaw: null, awayRaw: null });
    },
  );
  it("uses valid fair data and never invents a favorite for a tie", () => {
    const g = { ...game, homeMoneyline: -150, awayMoneyline: 130 };
    expect(favoriteOf(g)?.teamAbbr).toBe("BBB");
    const expectedHome = .6 / (.6 + 100 / 230);
    const expectedAway = 1 - expectedHome;
    expect(gameProbs(g, null).homeFair).toBeCloseTo(expectedHome, 12);
    expect(gameProbs(g, null).awayFair).toBeCloseTo(expectedAway, 12);
    expect(gameProbs(g, null).homeRaw).toBeCloseTo(.6, 12);
    expect(gameProbs(g, null).awayRaw).toBeCloseTo(100 / 230, 12);
    expect(buildRow(g).homePct).toBeCloseTo(expectedHome, 12);
    const tie = { ...g, homeMoneyline: -110, awayMoneyline: -110 };
    expect(favoriteOf(tie)).toBeNull();
    expect(buildRow(tie).favAbbr).toBeNull();
    const tieHtml = render(<><GameRow row={buildRow(tie)} /><MarketComparison game={tie} market={null} /></>);
    expect(tieHtml).toContain("AAA 50%");
    expect(tieHtml).toContain("BBB 50%");
    expect(tieHtml).toContain("50.0%");
    expect(tieHtml).not.toMatch(/Market favorite|Market edge|confidence/i);
    expect(gameProbs(game, { homeImpliedFair: NaN, awayImpliedFair: .4, homeImpliedRaw: null,
      awayImpliedRaw: null, vigPct: null, computedAt: null }).homeFair).toBeNull();
  });
  it("shows both market sources without confidence or edge indicators", () => {
    const g = { ...game, homeMoneyline: -150, awayMoneyline: 130 };
    const html = render(<><GameRow row={buildRow(g)} /><MarketComparison game={g} market={null} /></>);
    expect(html).toContain("Market probability");
    expect(html).toContain("implied probability after proportional vig removal");
    expect(html).toContain("Listed implied (incl. vig)");
    expect(html).toContain("60.0%");
    expect(html).not.toMatch(/confidence|edge|model/i);
  });
  it("preserves a valid market snapshot and its listed implied probabilities", () => {
    const g = { ...game, homeMoneyline: -150, awayMoneyline: 130 };
    const market = {
      homeImpliedFair: .64, awayImpliedFair: .36,
      homeImpliedRaw: .67, awayImpliedRaw: .38,
      vigPct: .05, computedAt: "2029-10-20T00:00:00Z",
    };
    expect(gameProbs(g, market)).toEqual({ homeFair: .64, awayFair: .36, homeRaw: .67, awayRaw: .38 });
    expect(buildRow({ ...g, market })).toMatchObject({ homePct: .64, awayPct: .36, favAbbr: "BBB" });
    const html = render(<MarketComparison game={g} market={market} />);
    expect(html).toContain("64.0%");
    expect(html).toContain("36.0%");
    expect(html).toContain("67.0%");
    expect(html).toContain("38.0%");
  });
  it("renders dropback rate as neutral style frequency", () => {
    const metric = { id: { season: 2029, week: 8, teamAbbr: "AAA" },
      offEpaPlay: .1, offEpaPass: .2, offEpaRush: -.1, defEpaPass: null,
      defEpaRush: null, dropbackRate: .623, playsOffense: 60 };
    const html = render(<TacticalComparison awayTeam={game.awayTeam} homeTeam={game.homeTeam}
      awayMetric={metric} homeMetric={{ ...metric, id: { ...metric.id, teamAbbr: "BBB" }, dropbackRate: .417 }} week={8} />);
    const dropback = html.slice(html.indexOf("Dropback Rate"));
    expect(dropback).toContain("62.3%");
    expect(dropback).toContain("41.7%");
    expect(dropback).toContain("Pass frequency");
    expect(dropback).toMatch(/opacity:0\.8/g);
    expect(dropback).not.toMatch(/winner|better|worse|edge/i);
  });
  it("renders a navigable no-odds row without highlights or fabricated percentages", () => {
    const html = render(<GameRow row={buildRow(game)} />);
    expect(html).toContain(`/game/${game.gameId}`);
    expect(html).toContain("Market unavailable");
    expect(html).toContain("AAA Team");
    expect(html).not.toMatch(/Model pick|confidence|—%|50%|class="gr-pct fav"/i);
  });
  it("keeps identity, date and cached analysis visible in a no-odds detail", () => {
    const cachedAnalysis = { fator_chave: "Cached key factor", veredito: "Cached verdict" };
    const html = render(<><MatchupHero game={game} awayPct={null} homePct={null} favAbbr={null}
      vig={null} weekLabel="Week 08" />
      <OverviewPanel game={game} favAbbr={null} awayPct={null} homePct={null}
        vig={null} predicao={cachedAnalysis}
        onViewAnalysis={vi.fn()} />
      <AnalysisSections predicao={cachedAnalysis} />
      <MarketComparison game={game} market={null} /></>);
    expect(html).toContain("AAA Team");
    expect(html).toContain("OCT 28");
    expect(html).toContain("Cached verdict");
    expect(html).toContain("View Analysis");
    expect(html).toContain("Key Factor");
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
    expect(html).not.toMatch(/Biggest Edge|favorite highlighted|Model Probability|—%/);
    const header = render(<SportsHeader season={2029} week={8} updatedLabel="Updated 1h ago" />);
    expect(header).toContain("2029");
    expect(header).toContain("Week 08");
    expect(header).not.toContain("2026");
  });
});
