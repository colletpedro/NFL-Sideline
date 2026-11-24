import { ArrowRight } from "lucide-react";
import type { Game, Predicao } from "../services/types";
import { fmtLine } from "../services/types";
import ProbabilitySplit from "./ProbabilitySplit";

function trim(text: string | undefined, max: number): string | null {
  if (!text) return null;
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  return `${clean.slice(0, max).trimEnd()}…`;
}

interface OverviewPanelProps {
  game: Game;
  favAbbr: string | null;
  awayPct: number | null;
  homePct: number | null;
  vig: number | null;
  predicao: Predicao | null;
  analysisLoading?: boolean;
  onViewAnalysis: () => void;
}

function OverviewPanel({
  game,
  favAbbr,
  awayPct,
  homePct,
  vig,
  predicao,
  analysisLoading,
  onViewAnalysis,
}: OverviewPanelProps) {
  const favPct = favAbbr === game.awayTeam.teamAbbr ? awayPct : favAbbr === game.homeTeam.teamAbbr ? homePct : null;

  const factors = [
    { no: "01", label: "Key Factor", text: trim(predicao?.fator_chave, 240), red: false },
    { no: "02", label: "Tactical Matchup", text: trim(predicao?.vantagem_tatica, 240), red: false },
    { no: "03", label: "Red Flag", text: trim(predicao?.alerta_vermelho, 240), red: true },
  ];
  const verdict = trim(predicao?.veredito, 260);

  return (
    <section className="overview">
      <div className="ov-pick">
        {favAbbr && favPct !== null ? <>
        <span className="k">Market favorite</span>
        <div className="ov-pick-main">
          <span className="abbr">{favAbbr}</span>
          <span className="pct">{favPct !== null ? `${(favPct * 100).toFixed(1)}%` : "—"}</span>
        </div>
        <span className="winlabel">
          Market probability
        </span>
        </> : <p>{awayPct === null || homePct === null ? "Market unavailable" : "No market favorite"}</p>}

        {awayPct !== null && homePct !== null && (
          <ProbabilitySplit
            size="lg"
            away={{ abbr: game.awayTeam.teamAbbr, pct: awayPct }}
            home={{ abbr: game.homeTeam.teamAbbr, pct: homePct }}
            favAbbr={favAbbr}
          />
        )}

        <div className="ov-data">
          <div className="cell">
            <span className="k">Spread</span>
            <span className="v">
              {fmtLine(game.spreadLine)}
            </span>
          </div>
          <div className="cell">
            <span className="k">Total</span>
            <span className="v">{game.totalLine !== null ? game.totalLine.toFixed(1) : "—"}</span>
          </div>
          <div className="cell">
            <span className="k">Vig</span>
            <span className="v">{vig !== null ? `${(vig * 100).toFixed(1)}%` : "—"}</span>
          </div>
        </div>

        {awayPct !== null && homePct !== null && <span className="winlabel">Implied probability after proportional vig removal</span>}
      </div>

      <div className="ov-factors">
        <div className="ov-factors-head">
          <span className="t">Top 3 Factors</span>
          <span className="s">Editorial analysis</span>
        </div>

        {analysisLoading ? (
          <div className="flex flex-col items-center justify-center py-12 animate-pulse text-gray-400">
            <span className="mb-2">Loading available analysis...</span>
            <div className="h-4 w-3/4 bg-gray-200 rounded mt-4"></div>
            <div className="h-4 w-1/2 bg-gray-200 rounded mt-2"></div>
            <div className="h-4 w-5/6 bg-gray-200 rounded mt-2"></div>
          </div>
        ) : (
          <>
            {factors.map((f) => (
              <div key={f.no} className="ov-factor">
                <span className="no">{f.no}</span>
                <div className="body">
                  <span className="k">{f.label}</span>
                  <p className={`t ${f.red ? "factor-red" : ""}`}>
                    {f.text ?? "Analysis not available yet"}
                  </p>
                </div>
              </div>
            ))}

            {verdict && (
              <div className="ov-verdict">
                <span className="k">Verdict</span>
                <p className="t">{verdict}</p>
              </div>
            )}

            <button className="ov-cta" onClick={onViewAnalysis}>
              {predicao ? "View Analysis" : "Analysis not available yet"}
              <ArrowRight size={14} strokeWidth={2.5} aria-hidden="true" />
            </button>
          </>
        )}
      </div>
    </section>
  );
}

export default OverviewPanel;
