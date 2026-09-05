import ProbabilitySplit from "./ProbabilitySplit";
import type { Game, MarketImplied } from "../services/types";
import { fmtLine, fmtNum, fmtPct, fmtTime } from "../services/types";

interface ModelReadoutProps {
  game: Game;
  market: MarketImplied | null;
  homePct: number | null;
  awayPct: number | null;
  favoriteAbbr: string;
  fromCache: boolean;
}

/**
 * MODEL READOUT — a statistics desk column. Compact mono rows with
 * right-aligned figures, separated by thin rules. No cards.
 */
function ModelReadout({ game, market, homePct, awayPct, favoriteAbbr, fromCache }: ModelReadoutProps) {
  const favSide: "left" | "right" = favoriteAbbr === game.homeTeam.teamAbbr ? "left" : "right";

  return (
    <aside className="readout">
      <h2 className="readout-title">Model Readout</h2>

      <div className="readout-row">
        <span className="k">{game.homeTeam.teamAbbr} / Home</span>
        <span className={`v ${favoriteAbbr === game.homeTeam.teamAbbr ? "fav" : ""}`}>
          {fmtPct(homePct)}
        </span>
      </div>
      <div className="readout-row">
        <span className="k">{game.awayTeam.teamAbbr} / Away</span>
        <span className={`v ${favoriteAbbr === game.awayTeam.teamAbbr ? "fav" : ""}`}>
          {fmtPct(awayPct)}
        </span>
      </div>
      {homePct !== null && awayPct !== null && (
        <div className="readout-split">
          <ProbabilitySplit
            left={{ abbr: game.homeTeam.teamAbbr, pct: (homePct ?? 0) * 100 }}
            right={{ abbr: game.awayTeam.teamAbbr, pct: (awayPct ?? 0) * 100 }}
            favSide={favSide}
          />
        </div>
      )}

      <div className="readout-row">
        <span className="k">Spread</span>
        <span className="v">{fmtLine(game.spreadLine)}</span>
      </div>
      <div className="readout-row">
        <span className="k">Total</span>
        <span className="v">{fmtNum(game.totalLine, 1)}</span>
      </div>
      <div className="readout-row">
        <span className="k">Vig</span>
        <span className="v gold">{market?.vigPct !== null && market?.vigPct !== undefined ? `${(market.vigPct * 100).toFixed(1)}%` : "—"}</span>
      </div>
      <div className="readout-row">
        <span className="k">Moneyline</span>
        <span className="v">
          {game.homeMoneyline !== null ? game.homeMoneyline : "—"} /{" "}
          {game.awayMoneyline !== null ? game.awayMoneyline : "—"}
        </span>
      </div>

      <div className="readout-meta">
        <div>Model Release 01</div>
        <div>Updated {fmtTime(market?.computedAt ?? null)}</div>
        <div>{fromCache ? "From cache" : "Fresh output"}</div>
      </div>
    </aside>
  );
}

export default ModelReadout;