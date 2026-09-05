import type { Team, TeamWeekMetrics } from "../services/types";
import { fmtNum } from "../services/types";
import { teamColor } from "../services/teamColors";

interface TacticalComparisonProps {
  awayTeam: Team;
  homeTeam: Team;
  awayMetric: TeamWeekMetrics | null;
  homeMetric: TeamWeekMetrics | null;
  week: number;
}

interface MetricSpec {
  key: "offEpaPlay" | "offEpaPass" | "offEpaRush" | "dropbackRate";
  label: string;
  hint: string;
  digits: number;
  /** Metric where a higher value is better (used to tint the winner). */
  higherIsBetter: boolean;
}

const METRICS: MetricSpec[] = [
  { key: "offEpaPlay", label: "EPA / Play", hint: "Offense", digits: 3, higherIsBetter: true },
  { key: "offEpaPass", label: "Passing EPA", hint: "Air game", digits: 3, higherIsBetter: true },
  { key: "offEpaRush", label: "Rushing EPA", hint: "Ground game", digits: 3, higherIsBetter: true },
  { key: "dropbackRate", label: "Dropback Rate", hint: "Pass tendency", digits: 0, higherIsBetter: false },
];

function TacticalComparison({ awayTeam, homeTeam, awayMetric, homeMetric, week }: TacticalComparisonProps) {
  if (!awayMetric && !homeMetric) {
    return (
      <section className="tactical">
        <div className="tac-empty">
          No play-by-play data for week {week} yet.
          <br />
          Efficiency metrics populate after the game is played.
        </div>
      </section>
    );
  }

  return (
    <section className="tactical">
      <div className="tac-head">
        <span className="t">Efficiency Snapshot</span>
        <span className="s">Week {String(week).padStart(2, "0")} · EPA per play</span>
      </div>

      {METRICS.map((m) => {
        const away = awayMetric?.[m.key];
        const home = homeMetric?.[m.key];
        if (away === null || away === undefined || home === null || home === undefined) return null;
        const maxAbs = Math.max(Math.abs(away), Math.abs(home), 0.0001);
        const awayWins = m.higherIsBetter ? away >= home : away < home;
        const homeWins = !awayWins;
        const awayWidth = m.key === "dropbackRate" ? away * 100 : (Math.abs(away) / maxAbs) * 100;
        const homeWidth = m.key === "dropbackRate" ? home * 100 : (Math.abs(home) / maxAbs) * 100;

        return (
          <div key={m.key} className="tac-metric">
            <div className="tac-metric-label">
              <span className="k">{m.label}</span>
              <span className="hint">{m.hint}</span>
            </div>

            <div className="tac-team">
              <span className="abbr">{awayTeam.teamAbbr}</span>
              <span className="bar">
                <span
                  className="fill"
                  style={{
                    width: `${Math.min(100, Math.max(0, awayWidth))}%`,
                    background: teamColor(awayTeam.teamAbbr),
                    opacity: awayWins ? 0.95 : 0.35,
                  }}
                />
              </span>
              <span className="val">{fmtNum(away, m.digits)}</span>
            </div>

            <div className="tac-team">
              <span className="abbr">{homeTeam.teamAbbr}</span>
              <span className="bar">
                <span
                  className="fill"
                  style={{
                    width: `${Math.min(100, Math.max(0, homeWidth))}%`,
                    background: teamColor(homeTeam.teamAbbr),
                    opacity: homeWins ? 0.95 : 0.35,
                  }}
                />
              </span>
              <span className="val">{fmtNum(home, m.digits)}</span>
            </div>
          </div>
        );
      })}
    </section>
  );
}

export default TacticalComparison;