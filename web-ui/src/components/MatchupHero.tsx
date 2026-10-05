import type { Game } from "../services/types";
import { dayDateOf } from "../services/market";
import { fmtLine } from "../services/types";
import ProbabilitySplit from "./ProbabilitySplit";
import { finalGameResult } from "./matchupResult";

interface MatchupHeroProps {
  game: Game;
  awayPct: number | null;
  homePct: number | null;
  favAbbr: string | null;
  vig: number | null;
  weekLabel: string;
}

function MatchupHero({
  game,
  awayPct,
  homePct,
  favAbbr,
  vig,
  weekLabel,
}: MatchupHeroProps) {
  const finalResult = finalGameResult(game);
  const isPregame = game.homeScore === null && game.awayScore === null && game.result === null;
  const showPregameMarket = finalResult === null && isPregame;
  const awayFav = showPregameMarket && favAbbr === game.awayTeam.teamAbbr;
  const homeFav = showPregameMarket && favAbbr === game.homeTeam.teamAbbr;
  const awayPrimary = finalResult
    ? String(finalResult.awayScore)
    : showPregameMarket && awayPct !== null
      ? `${(awayPct * 100).toFixed(1)}%`
      : "—";
  const homePrimary = finalResult
    ? String(finalResult.homeScore)
    : showPregameMarket && homePct !== null
      ? `${(homePct * 100).toFixed(1)}%`
      : "—";
  const awayPrimaryLabel = finalResult
    ? `${game.awayTeam.teamAbbr} score ${finalResult.awayScore}`
    : showPregameMarket && awayPct !== null
      ? `${game.awayTeam.teamAbbr} market probability ${(awayPct * 100).toFixed(1)} percent`
      : `${game.awayTeam.teamAbbr} primary value unavailable`;
  const homePrimaryLabel = finalResult
    ? `${game.homeTeam.teamAbbr} score ${finalResult.homeScore}`
    : showPregameMarket && homePct !== null
      ? `${game.homeTeam.teamAbbr} market probability ${(homePct * 100).toFixed(1)} percent`
      : `${game.homeTeam.teamAbbr} primary value unavailable`;

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
          <span
            className={`mu-pct ${finalResult ? "mu-score" : ""} ${awayFav ? "fav" : ""}`.trim()}
            aria-label={awayPrimaryLabel}
          >
            {awayPrimary}
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
          <span
            className={`mu-pct ${finalResult ? "mu-score" : ""} ${homeFav ? "fav" : ""}`.trim()}
            aria-label={homePrimaryLabel}
          >
            {homePrimary}
          </span>
        </div>
      </div>

      {finalResult ? (
        <p className="mu-favline mu-resultline">{finalResult.label}</p>
      ) : favAbbr ? <p className="mu-favline pick">Market favorite: {favAbbr}</p> : <p className="mu-favline">{homePct === null ? "Market unavailable" : "No market favorite"}</p>}

      <div className="mu-board">
        <div className="mu-board-split">
          {awayPct !== null && homePct !== null ? (
            <>
            <span className="mu-board-label">Market probability</span>
            <ProbabilitySplit
              away={{ abbr: game.awayTeam.teamAbbr, pct: awayPct }}
              home={{ abbr: game.homeTeam.teamAbbr, pct: homePct }}
              favAbbr={favAbbr}
            />
            </>
          ) : (
            <span className="mu-board-cell" style={{ padding: 0 }}>
              <span className="k">Market probability</span>
              <span className="v">Unavailable</span>
            </span>
          )}
        </div>

        <div className="mu-board-cell">
          <span className="k">Spread</span>
          <span className="v">
            {fmtLine(game.spreadLine)}
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

      </div>
    </header>
  );
}

export default MatchupHero;
