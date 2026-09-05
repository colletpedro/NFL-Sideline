import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import type { RowData } from "../services/model";
import { fmtEdge } from "../services/model";
import { fmtLine } from "../services/types";

interface ModelSignalProps {
  row: RowData;
}

function ModelSignal({ row }: ModelSignalProps) {
  const { game, favAbbr, favPct, edge } = row;

  return (
    <Link to={`/game/${game.gameId}`} className="model-signal">
      <div className="ms-label">
        <span className="k">Model Signal</span>
        <span className="t">Biggest Edge</span>
      </div>

      <div className="ms-matchup">
        <span className="ms-logos">
          {game.awayTeam.logoUrl && <img src={game.awayTeam.logoUrl} alt="" loading="lazy" />}
          {game.homeTeam.logoUrl && <img src={game.homeTeam.logoUrl} alt="" loading="lazy" />}
        </span>
        <span className="ms-name">
          {game.awayTeam.teamName} <span className="at">@</span> {game.homeTeam.teamName}
        </span>
      </div>

      <div className="ms-stats">
        <span className="ms-stat">
          <span className="k">{favAbbr}</span>
          <span className="v lime">{favPct !== null ? (favPct * 100).toFixed(0) : "—"}%</span>
        </span>
        <span className="ms-stat">
          <span className="k">Spread</span>
          <span className="v">
            {favAbbr} {fmtLine(game.spreadLine)}
          </span>
        </span>
        <span className="ms-edge">Edge {fmtEdge(edge)} pts</span>
        <ChevronRight className="ms-chev" size={18} strokeWidth={2.5} aria-hidden="true" />
      </div>
    </Link>
  );
}

export default ModelSignal;