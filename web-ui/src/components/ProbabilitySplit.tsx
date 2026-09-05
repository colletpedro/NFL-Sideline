interface ProbabilitySplitProps {
  /** Left segment — the away team. */
  away: { abbr: string; pct: number };
  /** Right segment — the home team. */
  home: { abbr: string; pct: number };
  /** Which team the model favors — its segment gets the signal color. */
  favAbbr: string;
  size?: "sm" | "md" | "lg";
  showLabels?: boolean;
}

function pct(v: number): number {
  return Math.min(100, Math.max(0, v * 100));
}

/**
 * Probability split — pure CSS comparative bar. The favorite's segment
 * renders in the model signal color, the other side stays muted.
 * Bar segments animate in once on mount.
 */
function ProbabilitySplit({ away, home, favAbbr, size = "md", showLabels = true }: ProbabilitySplitProps) {
  const awayFav = favAbbr === away.abbr;

  return (
    <span className={`split ${size}`}>
      {showLabels && (
        <span className="split-labels">
          <span className={awayFav ? "fav" : undefined}>
            {away.abbr} {pct(away.pct).toFixed(0)}%
          </span>
          <span className={!awayFav ? "fav" : undefined}>
            {home.abbr} {pct(home.pct).toFixed(0)}%
          </span>
        </span>
      )}
      <span className="split-bar" aria-hidden="true">
        <span
          className={`side ${awayFav ? "side-fav" : "side-dog"}`}
          style={{ width: `${pct(away.pct)}%` }}
        />
        <span
          className={`side ${awayFav ? "side-dog" : "side-fav"}`}
          style={{ width: `${pct(home.pct)}%` }}
        />
      </span>
    </span>
  );
}

export default ProbabilitySplit;