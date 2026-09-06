import { ArrowRight } from "lucide-react";
import type { Game, Predicao, Team } from "../services/types";
import type { Confidence } from "../services/model";
import { fmtEdge } from "../services/model";
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
  favTeam: Team;
  dogTeam: Team;
  favAbbr: string;
  favPct: number | null;
  dogPct: number | null;
  confidence: Confidence | null;
  edge: number | null;
  vig: number | null;
  predicao: Predicao | null;
  analysisLoading?: boolean;
  onViewAnalysis: () => void;
}

function OverviewPanel({
  game,
  favTeam,
  dogTeam,
  favAbbr,
  favPct,
  dogPct,
  confidence,
  edge,
  vig,
  predicao,
  analysisLoading,
  onViewAnalysis,
}: OverviewPanelProps) {
  const awayFav = favAbbr === game.awayTeam.teamAbbr;
  const awayPct = awayFav ? favPct : dogPct;
  const homePct = awayFav ? dogPct : favPct;

  const factors = [
    { no: "01", label: "Key Factor", text: trim(predicao?.fator_chave, 240), red: false },
    { no: "02", label: "Tactical Edge", text: trim(predicao?.vantagem_tatica, 240), red: false },
    { no: "03", label: "Red Flag", text: trim(predicao?.alerta_vermelho, 240), red: true },
  ];
  const verdict = trim(predicao?.veredito, 260);

  return (
    <section className="overview">
      <div className="ov-pick">
        <span className="k">Model Pick</span>
        <div className="ov-pick-main">
          <span className="abbr">{favAbbr}</span>
          <span className="pct">{favPct !== null ? `${(favPct * 100).toFixed(1)}%` : "—"}</span>
        </div>
        <span className="winlabel">
          Win probability{confidence ? ` · ${confidence} confidence` : ""}
        </span>

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
              {favTeam.teamAbbr} {fmtLine(game.spreadLine)}
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

        <span className="ov-edge">
          Model edge {fmtEdge(edge)} pts vs. even · {dogTeam.teamName} at{" "}
          {dogPct !== null ? `${(dogPct * 100).toFixed(1)}%` : "—"}
        </span>
      </div>

      <div className="ov-factors">
        <div className="ov-factors-head">
          <span className="t">Top 3 Factors</span>
          <span className="s">Model reasoning</span>
        </div>

        {analysisLoading ? (
          <div className="flex flex-col items-center justify-center py-12 animate-pulse text-gray-400">
            <span className="mb-2">Model is crunching data...</span>
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
                    {f.text ?? "Analysis not available for this game."}
                  </p>
                </div>
              </div>
            ))}

            {verdict && (
              <div className="ov-verdict">
                <span className="k">Model Verdict</span>
                <p className="t">{verdict}</p>
              </div>
            )}

            <button className="ov-cta" onClick={onViewAnalysis}>
              View Full Analysis
              <ArrowRight size={14} strokeWidth={2.5} aria-hidden="true" />
            </button>
          </>
        )}
      </div>
    </section>
  );
}

export default OverviewPanel;