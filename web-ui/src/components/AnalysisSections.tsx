import type { Predicao } from "../services/types";

const FALLBACK = "The model's analysis is not available for this game.";

interface AnalysisSectionsProps {
  predicao: Predicao | null;
}

function AnalysisSections({ predicao }: AnalysisSectionsProps) {
  return (
    <section className="analysis">
      <div className="an-section">
        <span className="an-no">01</span>
        <h2 className="an-head">Key Factor</h2>
        <p className="an-body">{predicao?.fator_chave ?? FALLBACK}</p>
      </div>

      <div className="an-section">
        <span className="an-no">02</span>
        <h2 className="an-head">Tactical Edge</h2>
        <p className="an-body">{predicao?.vantagem_tatica ?? FALLBACK}</p>
      </div>

      <div className="red-flag">
        <span className="an-no">03</span>
        <h2 className="an-head">Red Flag</h2>
        <p className="an-body">{predicao?.alerta_vermelho ?? FALLBACK}</p>
      </div>

      <div className="an-verdict">
        <span className="an-no">04</span>
        <h2 className="an-head">Model Verdict</h2>
        <p className="an-body">{predicao?.veredito ?? FALLBACK}</p>
      </div>
    </section>
  );
}

export default AnalysisSections;