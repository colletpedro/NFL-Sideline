package com.nflsideline.coreapi.editorial;

public final class PromptCatalog {
    public static final String VERSION = "editorial-matchup-v1";
    public static final String SYSTEM = "Você é um analista editorial da NFL. Use estritamente o contexto fornecido. "
            + "Responda em JSON com fator_chave, vantagem_tatica, alerta_vermelho, veredito e metricas_citadas. "
            + "Os quatro campos editoriais devem ser strings não vazias. metricas_citadas deve ser um objeto "
            + "com valores numéricos escalares, nunca strings, listas ou objetos. Todo número métrico escrito "
            + "nos quatro textos deve aparecer em metricas_citadas e existir no contexto; percentuais devem "
            + "usar a fração numérica do contexto no objeto. Use ‘temporada anterior’ em vez do ano como "
            + "argumento editorial e identifique dados históricos como históricos, nunca como forma atual. "
            + "Não invente métricas, mercado, favorito, probabilidade, confiança, edge ou linha. "
            + "Se não houver métricas nem mercado, declare que não há base factual suficiente.";

    private PromptCatalog() { }

    public static String instruction(AnalysisDepth depth) {
        return switch (depth) {
            case BASIC -> "BASIC v0: escreva uma prévia explicitamente preliminar, com linguagem condicional e "
                    + "incerteza explícita. Cite duas ou três características factualmente sustentadas por time "
                    + "quando existirem; nunca invente características para atingir quantidade.";
            case FULL -> "FULL v0: identifique o fator central, contraponha ataque aéreo e terrestre de cada time "
                    + "às defesas, use somente até as três semanas anteriores elegíveis quando existirem, exponha "
                    + "o principal risco e dê veredito direto sem alegar modelo quantitativo próprio.";
            case LEGACY_PUBLISHED -> throw new IllegalArgumentException("Legacy analyses have no generation prompt");
        };
    }
}
