import type { Game } from "../services/types";
import type { Confidence } from "../services/model";
import { dayDateOf, fmtEdge } from "../services/model";
import { fmtLine } from "../services/types";
import ProbabilitySplit from "./ProbabilitySplit";

const CONF_DOT: Record<string, string> = {
  HIGH: "#D7FF3F",
  MEDIUM: "#9AA0A8",
  LOW: "#6B7280",
};

interface MatchupHeroProps {
  game: Game;
  awayPct: number | null;
  homePct: number | null;
  favAbbr: string;
  confidence: Confidence | null;
  edge: number | null;
  vig: number | null;
  weekLabel: string;
}

function MatchupHero({
  game,
  awayPct,
  homePct,
  favAbbr,
  confidence,
  edge,
  vig,
  weekLabel,
}: MatchupHeroProps) {
  const awayFav = favAbbr === game.awayTeam.teamAbbr;
  const dotColor = confidence ? CONF_DOT[confidence] : "#6B7280";

  return (
    <header className="mu-hero">
      <p className="mu-kicker">
        {weekLabel} · {dayDateOf(game.gameday)}
      </p>

      <div className="mu-grid">
        <div className="mu-team away">
          <div className="mu-team-top">
            <div>
              <div className="mu-name">{game.awayTeam.teamName}</div>
              <div className="mu-sub">
                {game.awayTeam.teamAbbr} · Away
              </div>
            </div>
            {game.awayTeam.logoUrl && (
              <img className="mu-logo" src={game.awayTeam.logoUrl} alt="" />
            )}
          </div>
          <span className={`mu-pct ${awayFav ? "fav" : ""}`}>
            {awayPct !== null ? `${(awayPct * 100).toFixed(1)}%` : "—"}
          </span>
        </div>

        <span className="mu-at" aria-hidden="true">
          @
        </span>

        <div className="mu-team home">
          <div className="mu-team-top">
            {game.homeTeam.logoUrl && (
              <img className="mu-logo" src={game.homeTeam.logoUrl} alt="" />
            )}
            <div>
              <div className="mu-name">{game.homeTeam.teamName}</div>
              <div className="mu-sub">
                {game.homeTeam.teamAbbr} · Home
              </div>
            </div>
          </div>
          <span className={`mu-pct ${!awayFav ? "fav" : ""}`}>
            {homePct !== null ? `${(homePct * 100).toFixed(1)}%` : "—"}
          </span>
        </div>
      </div>

      <div className="mu-favline">
        <span className="pick">Model favorite: {favAbbr}</span>
        <span className="sep">·</span>
        {confidence && (
          <span className="conf">
            <i className="dot" style={{ background: dotColor }} aria-hidden="true" />
            {confidence} confidence
          </span>
        )}
        <span className="sep">·</span>
        <span className="edge">Edge {fmtEdge(edge)} pts</span>
      </div>

      <div className="mu-board">
        <div className="mu-board-split">
          {awayPct !== null && homePct !== null ? (
            <ProbabilitySplit
              away={{ abbr: game.awayTeam.teamAbbr, pct: awayPct }}
              home={{ abbr: game.homeTeam.teamAbbr, pct: homePct }}
              favAbbr={favAbbr}
            />
          ) : (
            <span className="mu-board-cell" style={{ padding: 0 }}>
              <span className="k">Probability</span>
              <span className="v">—</span>
            </span>
          )}
        </div>

        <div className="mu-board-cell">
          <span className="k">Model spread</span>
          <span className="v">
            <span className="fav-abbr">{favAbbr}</span> {fmtLine(game.spreadLine)}
          </span>
        </div>

        <div className="mu-board-cell">
          <span className="k">Total</span>
          <span className="v">{game.totalLine !== null ? game.totalLine.toFixed(1) : "—"}</span>
        </div>

        <div className="mu-board-cell">
          <span className="k">Vig</span>
          <span className="v">{vig !== null ? `${(vig * 100).toFixed(1)}%` : "—"}</span>
        </div>

        <div className="mu-board-cell">
          <span className="k">Model edge</span>
          <span className="v lime">{fmtEdge(edge)} pts</span>
        </div>
      </div>
    </header>
  );
}

export default MatchupHero;