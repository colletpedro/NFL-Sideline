import type { Predicao } from "../services/types";

const FALLBACK = "The model's analysis is not available for this game.";

interface AnalysisSectionsProps {
  predicao: Predicao | null;
  analysisLoading?: boolean;
}

function AnalysisSections({ predicao, analysisLoading }: AnalysisSectionsProps) {
  if (analysisLoading) {
    return (
      <section className="analysis py-12 flex flex-col items-center animate-pulse">
        <span className="text-gray-500 text-lg mb-8">Model is crunching data...</span>
        <div className="w-full max-w-2xl space-y-6">
          <div className="h-6 w-1/4 bg-gray-200 rounded"></div>
          <div className="h-4 w-full bg-gray-200 rounded"></div>
          <div className="h-4 w-5/6 bg-gray-200 rounded"></div>
          <div className="h-4 w-4/6 bg-gray-200 rounded"></div>
        </div>
      </section>
    );
  }

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