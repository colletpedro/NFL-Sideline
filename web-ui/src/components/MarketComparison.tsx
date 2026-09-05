import type { Game, MarketImplied } from "../services/types";
import { fmtEdge, gameProbs } from "../services/model";
import { fmtLine, fmtNum } from "../services/types";

interface MarketComparisonProps {
  game: Game;
  market: MarketImplied | null;
  favAbbr: string;
  edge: number | null;
}

function pct(v: number | null | undefined): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(1)}%`;
}

function MarketComparison({ game, market, favAbbr, edge }: MarketComparisonProps) {
  const probs = gameProbs(game, market);
  const homeFav = favAbbr === game.homeTeam.teamAbbr;
  const modelPct = homeFav ? probs.homeModel : probs.awayModel;
  const marketPct = homeFav ? probs.homeRaw : probs.awayRaw;
  const vig = market?.vigPct ?? null;

  const modelWidth = modelPct !== null ? modelPct * 100 : 0;
  const marketWidth = marketPct !== null ? marketPct * 100 : 0;

  return (
    <section className="market">
      <div className="mc-compare">
        <div className="mc-cell">
          <span className="k">Model</span>
          <span className="v">
            {favAbbr} {pct(modelPct)}
          </span>
          <span className="d">Vig-free fair value</span>
        </div>
        <div className="mc-cell">
          <span className="k">Market implied</span>
          <span className="v">
            {favAbbr} {pct(marketPct)}
          </span>
          <span className="d">Listed price, incl. vig</span>
        </div>
        <div className="mc-cell">
          <span className="k">Model edge</span>
          <span className="v lime">{fmtEdge(edge)} pts</span>
          <span className="d">Model read vs. 50/50</span>
        </div>
      </div>

      <div className="mc-bars">
        <div className="mc-bar-row">
          <div className="mc-bar-top">
            <span>Model — fair value</span>
            <span className="val">{pct(modelPct)}</span>
          </div>
          <div className="mc-bar model">
            <div
              className="fill"
              style={{ width: `${Math.min(100, modelWidth)}%` }}
            />
          </div>
        </div>
        <div className="mc-bar-row">
          <div className="mc-bar-top">
            <span>Market — listed (incl. vig)</span>
            <span className="val">{pct(marketPct)}</span>
          </div>
          <div className="mc-bar market">
            <div
              className="fill"
              style={{ width: `${Math.min(100, marketWidth)}%` }}
            />
          </div>
        </div>
      </div>

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
          <span className="v lime">{vig !== null ? `${(vig * 100).toFixed(1)}%` : "—"}</span>
        </div>
      </div>
    </section>
  );
}

export default MarketComparison;