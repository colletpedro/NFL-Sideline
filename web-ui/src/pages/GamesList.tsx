import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../services/api";

interface Team {
  teamAbbr: string;
  teamName: string;
}

interface Game {
  gameId: string;
  season: number;
  week: number;
  gameday: string;
  homeTeam: Team;
  awayTeam: Team;
  homeScore: number | null;
  awayScore: number | null;
}

const SEASON = 2026;

function formatDate(isoDate: string): string {
  return new Date(`${isoDate}T00:00:00Z`).toLocaleDateString("pt-BR", {
    timeZone: "UTC",
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

function GamesList() {
  const [games, setGames] = useState<Game[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    api
      .get<Game[]>("/games", { params: { season: SEASON } })
      .then((response) => {
        if (!cancelled) setGames(response.data);
      })
      .catch(() => {
        if (!cancelled) setError("Falha ao carregar jogos.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, []);

  if (loading) {
    return <div>Carregando jogos...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

  if (games.length === 0) {
    return <div>Nenhum jogo encontrado para a temporada {SEASON}.</div>;
  }

  return (
    <div>
      <h1>NFL Games</h1>
      <ul className="games-grid">
        {games.map((game) => {
          const hasScore = game.homeScore !== null && game.awayScore !== null;
          return (
            <li key={game.gameId} className="game-card">
              <div className="game-matchup">
                {game.awayTeam.teamName} @ {game.homeTeam.teamName}
              </div>
              {hasScore && (
                <div className="game-score">
                  {game.awayScore} - {game.homeScore}
                </div>
              )}
              <div className="game-meta">
                Semana {game.week} • {formatDate(game.gameday)}
              </div>
              <Link to={`/game/${game.gameId}`} className="btn">
                Ver Análise RAG
              </Link>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

export default GamesList;
