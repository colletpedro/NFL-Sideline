import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import { Sparkles } from "lucide-react";
import {
  Bar,
  BarChart,
  Cell,
  Legend,
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

interface TeamWeekMetrics {
  id: { season: number; week: number; teamAbbr: string };
  offEpaPlay: number | null;
  offEpaPass: number | null;
  offEpaRush: number | null;
  defEpaPass: number | null;
  defEpaRush: number | null;
  dropbackRate: number | null;
  playsOffense: number | null;
}

interface GameDetail {
  game: Game;
  market: MarketImplied | null;
  homeMetrics: TeamWeekMetrics[];
  awayMetrics: TeamWeekMetrics[];
}

interface AnalysisResponse {
  gameId: string;
  markdownText: string;
  fromCache: boolean;
}

/** Normaliza número JSON (possivelmente null/ausente) para o Recharts. */
function toNumber(value: number | null | undefined): number | undefined {
  return value === null || value === undefined ? undefined : Number(value);
}

/**
 * Métrica do time para a semana do jogo. Prefere a semana exata do confronto;
 * se ainda não houver dado (jogo futuro), cai para a última semana jogada
 * (week <= alvo) e, por fim, para o último registro da série.
 */
function metricForWeek(
  series: TeamWeekMetrics[] | undefined,
  week: number
): TeamWeekMetrics | null {
  if (!series || series.length === 0) return null;
  const exact = series.find((m) => m.id.week === week);
  if (exact) return exact;
  let latestBefore: TeamWeekMetrics | null = null;
  for (const m of series) {
    if (m.id.week <= week) latestBefore = m;
  }
  return latestBefore ?? series[series.length - 1];
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

  // Métricas avançadas: registro da semana do jogo para cada time
  const homeMetric = game ? metricForWeek(detail?.homeMetrics, game.week) : null;
  const awayMetric = game ? metricForWeek(detail?.awayMetrics, game.week) : null;

  const efficiencyData =
    game && homeMetric && awayMetric
      ? [
          {
            name: game.homeTeam.teamAbbr,
            Passe: toNumber(homeMetric.offEpaPass),
            Corrida: toNumber(homeMetric.offEpaRush),
          },
          {
            name: game.awayTeam.teamAbbr,
            Passe: toNumber(awayMetric.offEpaPass),
            Corrida: toNumber(awayMetric.offEpaRush),
          },
        ]
      : null;

  const hasEfficiencyValues = efficiencyData?.some(
    (row) => row.Passe !== undefined || row.Corrida !== undefined
  );

  const dropbackLabel = (metric: TeamWeekMetrics | null, abbr: string) => {
    if (!metric || metric.dropbackRate === null || metric.dropbackRate === undefined) return null;
    return `${abbr} · Dropback ${(metric.dropbackRate * 100).toFixed(0)}%`;
  };

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

      <section className="dashboard-panel dashboard-advanced">
        <div className="panel-header">
          <h2>Eficiência por Tipo de Jogada</h2>
          <div className="dropback-badges">
            {game && dropbackLabel(homeMetric, game.homeTeam.teamAbbr) && (
              <span className="badge badge-team">{dropbackLabel(homeMetric, game.homeTeam.teamAbbr)}</span>
            )}
            {game && dropbackLabel(awayMetric, game.awayTeam.teamAbbr) && (
              <span className="badge badge-team">{dropbackLabel(awayMetric, game.awayTeam.teamAbbr)}</span>
            )}
          </div>
        </div>
        {efficiencyData && hasEfficiencyValues ? (
            <>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={efficiencyData}>
                  <XAxis dataKey="name" />
                  <YAxis width={52} />
                  <Tooltip formatter={(value) => Number(value).toFixed(3)} />
                  <Legend />
                  <Bar dataKey="Passe" fill="#6366f1" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="Corrida" fill="#f59e0b" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
              <p className="market-legend">
                EPA médio por jogada de passe vs corrida {game ? `— semana ${game.week}` : ""}
              </p>
            </>
          ) : (
            <p>Métricas por tipo de jogada ainda não disponíveis para este jogo.</p>
          )}
      </section>
    </div>
  );
}

export default MatchupDashboard;
