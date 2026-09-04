import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import { Sparkles } from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
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
  spreadLine: number | null;
  totalLine: number | null;
}

interface MarketImplied {
  homeImpliedFair: number | null;
  awayImpliedFair: number | null;
  vigPct: number | null;
}

interface GameDetail {
  game: Game;
  market: MarketImplied | null;
}

interface AnalysisResponse {
  gameId: string;
  markdownText: string;
  fromCache: boolean;
}

function MatchupDashboard() {
  const { id } = useParams<{ id: string }>();
  const [detail, setDetail] = useState<GameDetail | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;

    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      api.get<GameDetail>(`/games/${id}`),
      api.post<AnalysisResponse>("/analysis/matchup", {
        gameId: id,
        analysisType: "matchup",
      }),
    ])
      .then(([detailResponse, analysisResponse]) => {
        if (cancelled) return;
        setDetail(detailResponse.data);
        setAnalysis(analysisResponse.data);
      })
      .catch((err) => {
        if (cancelled) return;
        if (axios.isAxiosError(err) && err.response?.status === 404) {
          setError("Jogo não encontrado.");
        } else if (axios.isAxiosError(err) && err.response?.status === 503) {
          setError("Falha do modelo de IA ao gerar a análise.");
        } else {
          setError("Falha ao carregar análise.");
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [id]);

  if (loading) {
    return <div>Carregando análise tática...</div>;
  }

  if (error) {
    return <div>{error}</div>;
  }

  const { game, market } = detail ?? { game: null, market: null };
  const homeFair = market?.homeImpliedFair;
  const awayFair = market?.awayImpliedFair;

  const chartData =
    game && homeFair !== null && homeFair !== undefined && awayFair !== null && awayFair !== undefined
      ? [
          { name: game.homeTeam.teamAbbr, prob: homeFair * 100, fill: "#2563eb" },
          { name: game.awayTeam.teamAbbr, prob: awayFair * 100, fill: "#dc2626" },
        ]
      : null;

  return (
    <div>
      <h1>
        {game ? `${game.awayTeam.teamName} @ ${game.homeTeam.teamName}` : "Matchup Analysis"}
      </h1>

      <div className="dashboard">
        <section className="dashboard-panel dashboard-ai">
          <div className="panel-header">
            <h2>Análise Tática</h2>
            <span className="badge">
              <Sparkles size={14} aria-hidden="true" />
              Powered by Gemini 2.5 Flash
              {analysis?.fromCache ? " (cache)" : ""}
            </span>
          </div>
          <div className="markdown-body">
            {analysis ? (
              <ReactMarkdown>{analysis.markdownText}</ReactMarkdown>
            ) : (
              <p>Nenhuma análise disponível.</p>
            )}
          </div>
        </section>

        <aside className="dashboard-panel dashboard-market">
          <h2>Mercado</h2>
          {chartData ? (
            <>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={chartData}>
                  <XAxis dataKey="name" />
                  <YAxis domain={[0, 100]} tickFormatter={(v) => `${v}%`} width={44} />
                  <Tooltip formatter={(value) => `${Number(value).toFixed(1)}%`} />
                  <Bar dataKey="prob" radius={[6, 6, 0, 0]}>
                    {chartData.map((entry) => (
                      <Cell key={entry.name} fill={entry.fill} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
              <p className="market-legend">
                Probabilidade justa de vitória (time da casa vs visitante)
              </p>
            </>
          ) : (
            <p>Dados de mercado ainda não calculados para este jogo.</p>
          )}

          {game && (
            <dl className="market-facts">
              {game.spreadLine !== null && game.spreadLine !== undefined && (
                <div>
                  <dt>Spread</dt>
                  <dd>{game.spreadLine}</dd>
                </div>
              )}
              {game.totalLine !== null && game.totalLine !== undefined && (
                <div>
                  <dt>Total</dt>
                  <dd>{game.totalLine}</dd>
                </div>
              )}
              {market?.vigPct !== null && market?.vigPct !== undefined && (
                <div>
                  <dt>Vig</dt>
                  <dd>{(Number(market.vigPct) * 100).toFixed(1)}%</dd>
                </div>
              )}
            </dl>
          )}
        </aside>
      </div>
    </div>
  );
}

export default MatchupDashboard;
