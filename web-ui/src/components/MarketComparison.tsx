import type { Game, MarketImplied } from "../services/types";
import { gameProbs } from "../services/market";
import { fmtLine, fmtNum } from "../services/types";

interface MarketComparisonProps {
  game: Game;
  market: MarketImplied | null;
}

function pct(value: number | null): string {
  return value === null ? "—" : `${(value * 100).toFixed(1)}%`;
}

function MarketComparison({ game, market }: MarketComparisonProps) {
  const probs = gameProbs(game, market);
  const vig = market?.vigPct ?? null;
  const hasFairMarket = probs.homeFair !== null && probs.awayFair !== null;

  return (
    <section className="market">
      {hasFairMarket ? <>
        <p className="mc-explanation">Market probability is implied probability after proportional vig removal. Listed implied probability includes vig.</p>
        <div className="mc-compare">
          <div className="mc-cell">
            <span className="k">{game.awayTeam.teamAbbr} · Away</span>
            <span className="v">{pct(probs.awayFair)}</span>
            <span className="d">Market probability</span>
            <span className="mc-raw">Listed implied (incl. vig) {pct(probs.awayRaw)}</span>
          </div>
          <div className="mc-cell">
            <span className="k">{game.homeTeam.teamAbbr} · Home</span>
            <span className="v">{pct(probs.homeFair)}</span>
            <span className="d">Market probability</span>
            <span className="mc-raw">Listed implied (incl. vig) {pct(probs.homeRaw)}</span>
          </div>
        </div>
      </> : <p className="page-state">Market unavailable. A complete valid moneyline pair is not available for this game.</p>}
      <div className="mc-data">
        <div className="cell">
          <span className="k">Moneyline</span>
          <span className="v">
            {game.homeMoneyline !== null ? `${game.homeTeam.teamAbbr} ${game.homeMoneyline}` : "—"}
            {game.awayMoneyline !== null ? ` / ${game.awayTeam.teamAbbr} ${game.awayMoneyline}` : ""}
          </span>
        </div>
        <div className="cell">
          <span className="k">Spread</span>
          <span className="v">{fmtLine(game.spreadLine)}</span>
        </div>
        <div className="cell">
          <span className="k">Total</span>
          <span className="v">{fmtNum(game.totalLine, 1)}</span>
        </div>
        <div className="cell">
          <span className="k">Vig</span>
          <span className="v">{vig !== null ? `${(vig * 100).toFixed(1)}%` : "—"}</span>
        </div>
      </div>
    </section>
  );
}

export default MarketComparison;
