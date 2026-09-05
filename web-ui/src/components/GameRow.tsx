import { Link } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import type { CSSProperties } from "react";
import type { RowData } from "../services/model";
import { teamColor } from "../services/teamColors";
import { fmtLine } from "../services/types";
import ProbabilitySplit from "./ProbabilitySplit";

const CONF_DOT: Record<string, string> = {
  HIGH: "#D7FF3F",
  MEDIUM: "#9AA0A8",
  LOW: "#6B7280",
};

interface GameRowProps {
  row: RowData;
}

function GameRow({ row }: GameRowProps) {
  const { game, favAbbr, favPct, dogPct, confidence, day, date } = row;
  const awayFav = favAbbr === game.awayTeam.teamAbbr;
  const awayPct = awayFav ? favPct : dogPct;
  const homePct = awayFav ? dogPct : favPct;

  const style = { "--fav-color": teamColor(favAbbr) } as CSSProperties;
  const dotColor = confidence ? CONF_DOT[confidence] : "#6B7280";

  return (
    <Link to={`/game/${game.gameId}`} className="game-row" style={style}>
      <span className="gr-day">
        <span className="d">{day}</span>
        <span className="dt">{date}</span>
        <span className="gr-mob-pick">Model pick {favAbbr}</span>
      </span>

      <span className="gr-team gr-away">
        <span className={`gr-pct ${awayFav ? "fav" : ""}`}>
          {awayPct !== null ? `${(awayPct * 100).toFixed(0)}%` : "—"}
        </span>
        <span className="gr-info">
          <span className="gr-name">{game.awayTeam.teamName}</span>
          <span className="gr-sub">
            {game.awayTeam.teamAbbr} · Away
          </span>
        </span>
        {game.awayTeam.logoUrl && (
          <img className="gr-logo" src={game.awayTeam.logoUrl} alt="" loading="lazy" />
        )}
      </span>

      <span className="gr-mid">
        {awayPct !== null && homePct !== null && (
          <ProbabilitySplit
            away={{ abbr: game.awayTeam.teamAbbr, pct: awayPct }}
            home={{ abbr: game.homeTeam.teamAbbr, pct: homePct }}
            favAbbr={favAbbr}
          />
        )}
        <span className="gr-meta">
          <span>{favAbbr} {fmtLine(game.spreadLine)}</span>
          <span>Total {game.totalLine !== null ? game.totalLine.toFixed(1) : "—"}</span>
        </span>
      </span>

      <span className="gr-team gr-home">
        <span className={`gr-pct ${!awayFav ? "fav" : ""}`}>
          {homePct !== null ? `${(homePct * 100).toFixed(0)}%` : "—"}
        </span>
        <span className="gr-info">
          <span className="gr-name">{game.homeTeam.teamName}</span>
          <span className="gr-sub">
            {game.homeTeam.teamAbbr} · Home
          </span>
        </span>
        {game.homeTeam.logoUrl && (
          <img className="gr-logo" src={game.homeTeam.logoUrl} alt="" loading="lazy" />
        )}
      </span>

      <span className="gr-rail">
        {confidence && (
          <span className="gr-conf">
            <i className="dot" style={{ background: dotColor }} aria-hidden="true" />
            {confidence}
          </span>
        )}
        <span className="gr-view">View Prediction</span>
        <ChevronRight className="gr-chev" size={16} strokeWidth={2.5} aria-hidden="true" />
      </span>
    </Link>
  );
}

export default GameRow;