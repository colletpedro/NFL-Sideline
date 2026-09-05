interface ProbabilitySplitProps {
  left: { abbr: string; pct: number };
  right: { abbr: string; pct: number };
  /** Qual lado é o favorito — recebe a cor verde editorial. */
  favSide?: "left" | "right";
}

/**
 * Instrumento de probabilidade 100% CSS: uma barra dividida em dois
 * segmentos que desenham-se lentamente. Sem bibliotecas de gráficos.
 */
function ProbabilitySplit({ left, right, favSide }: ProbabilitySplitProps) {
  const l = Math.min(100, Math.max(0, left.pct));
  const r = Math.min(100, Math.max(0, right.pct));

  return (
    <span className="split">
      <span className="split-bar" aria-hidden="true">
        <span className="side side-left" style={{ width: `${l}%` }} />
        <span className="side side-right" style={{ width: `${r}%` }} />
      </span>
      <span className="split-labels">
        <span className={favSide === "left" ? "fav" : undefined}>
          {left.abbr} {left.pct.toFixed(0)}%
        </span>
        <span className={favSide === "right" ? "fav" : undefined}>
          {right.abbr} {right.pct.toFixed(0)}%
        </span>
      </span>
    </span>
  );
}

export default ProbabilitySplit;