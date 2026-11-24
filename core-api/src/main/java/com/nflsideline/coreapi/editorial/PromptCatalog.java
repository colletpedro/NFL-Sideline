package com.nflsideline.coreapi.editorial;

public final class PromptCatalog {
    public static final String VERSION = "editorial-claims-v3";
    public static final String SYSTEM = "Você seleciona claims tipadas; o servidor valida relações e redige os quatro textos. "
            + "Responda somente no contrato JSON v3: contract_version=3, thesis_team (time ou NONE), "
            + "verdict (INCONCLUSIVE, SLIGHT_HOME, SLIGHT_AWAY), claims e sections. "
            + "Cada claim tem claim_id, type (OBSERVATION, COMPARISON, WINDOW_COMPARISON, MATCHUP, LIMITATION), subject, predicate, "
            + "period (CURRENT, HISTORICAL, NONE), evidence_ids, role (SUPPORT, COUNTER, LIMITATION) "
            + "e thesis_id para contraponto. Toda claim deve ser usada; pode reaparecer em seções diferentes, nunca duplicada na mesma seção. "
            + "COMPARISON usa duas evidências da mesma métrica, temporada e semana, em ordem sujeito/oponente. "
            + "WINDOW_COMPARISON usa dois IDs rw de recent_windows: mesma métrica, temporada, origem e aggregation; "
            + "as semanas podem diferir. Use GREATER_THAN ou LESS_THAN na ordem sujeito/oponente. "
            + "MATCHUP relaciona o ataque do subject à defesa adversária no mesmo fundamento: OFF_EPA_PASS/DEF_EPA_PASS, "
            + "OFF_EPA_RUSH/DEF_EPA_RUSH ou OFF_EPA_PLAY/DEF_EPA_PLAY. evidence_ids contém os dois IDs rw, ataque primeiro. "
            + "ATTACK_DEFENSE_PROFILE usa role LIMITATION e apenas descreve o encontro; permite veredito INCONCLUSIVE. "
            + "POSITIVE_EPA_CONVERGENCE usa role SUPPORT ou COUNTER, period CURRENT, apenas quando minimum > 0 nas duas janelas "
            + "e missingMetricWeeks está vazio em ambas. É convergência descritiva de sinais, não qualidade relativa à liga nem exploração comprovada. "
            + "Não compare numericamente EPA ofensivo com EPA defensivo nem use média positiva para esconder semanas negativas. "
            + "fator_chave tem uma claim principal. vantagem_tatica tem uma MATCHUP ou limitação NO_MATCHUP_SUPPORT. "
            + "Inclinação só pode apoiar MATCHUP POSITIVE_EPA_CONVERGENCE do time da tese; inconclusivo continua permitido. "
            + "NO_MATCHUP_SUPPORT só vale se não existir convergência elegível para nenhum time. Um PROFILE não nega a existência de sinais. "
            + "alerta_vermelho tem um contraponto favorável ao adversário (COMPARISON, WINDOW_COMPARISON ou MATCHUP) "
            + "com thesis_id igual à claim do fator_chave, ou uma limitação factual. veredito tem uma limitação. "
            + "Limitações: NO_DATA (nenhuma métrica), PARTIAL_DATA (um time sem métricas), HISTORICAL_ONLY (só histórico), "
            + "SMALL_SAMPLE (algum dado atual e ao menos um time com até duas semanas atuais), LIMITED_WINDOW (até três semanas), "
            + "UNEVEN_WINDOWS (semanas atuais diferentes entre times), MIXED_SIGNALS (EPA positivo e negativo numa mesma janela). "
            + "Prefira recortes completos e contrapontos relevantes ao fundamento da tese; trate observação isolada como secundária. "
            + "Não use mercado, previsão causal ou identidade permanente. Cobertura de dados não é suficiência de amostra.";

    private PromptCatalog() { }

    public static String instruction(AnalysisDepth depth) {
        return switch (depth) {
            case BASIC -> "BASIC v3: escolha um perfil ataque-defesa relevante e explicite cobertura e limitações; inconclusivo é válido.";
            case FULL -> "FULL v3: priorize o encontro ataque-defesa no mesmo fundamento sobre os recortes completos; "
                    + "selecione contraponto relevante ou limitação e preserve a ambiguidade no veredito.";
            case LEGACY_PUBLISHED -> throw new IllegalArgumentException("Legacy analyses have no generation prompt");
        };
    }
}
