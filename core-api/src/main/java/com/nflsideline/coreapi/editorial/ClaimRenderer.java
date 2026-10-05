package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.math.RoundingMode;
import java.text.DecimalFormat;
import java.text.DecimalFormatSymbols;
import java.util.*;
import static com.nflsideline.coreapi.editorial.ClaimValidator.*;

/** Controlled realization after semantic validation; the JSON entry point preserves v3 callers. */
public final class ClaimRenderer {
    public static final String VERSION = "controlled-claims-v5.0.2";
    private final ObjectMapper mapper;
    public ClaimRenderer(ObjectMapper mapper) { this.mapper = mapper; }
    public ObjectNode render(JsonNode root, AnalysisContext context) {
        return render(new ClaimValidator().validate(root, context));
    }
    public ObjectNode render(ValidatedClaims validated) {
        if (validated.version() == 5) return new SignalClaimRenderer(mapper).render(validated.signals());
        if (validated.version() == 4) return renderNeutral(validated);
        var sections = validated.sections();
        String thesis = validated.thesis(), verdict = validated.verdict();
        var key = sections.get("fator_chave");
        var advantage = sections.get("vantagem_tatica");
        var red = sections.get("alerta_vermelho");
        var conclusion = sections.get("veredito");
        boolean demonstrated = advantage.stream().anyMatch(c -> c.predicate() == Predicate.POSITIVE_EPA_CONVERGENCE);
        ObjectNode out = mapper.createObjectNode();
        out.put("fator_chave", sentence(key.getFirst()));
        out.put("vantagem_tatica", demonstrated
                ? sentence(advantage.getFirst())
                : sentence(advantage.getFirst()) + " Esse recorte não estabelece uma vantagem para o confronto.");
        out.put("alerta_vermelho", red.getFirst().role() == Role.COUNTER
                ? "Contraponto: " + sentence(red.getFirst())
                : "Limitação: " + sentence(red.getFirst()));
        out.put("veredito", (verdict.equals("INCONCLUSIVE")
                ? "O confronto permanece inconclusivo nos dados disponíveis. " + sentence(conclusion.getFirst())
                : "Há leve inclinação descritiva para " + thesis + ", limitada aos recortes observados. "
                + sentence(conclusion.getFirst()))
                + (red.getFirst().role() == Role.COUNTER ? " A ressalva permanece: " + sentence(red.getFirst()) : ""));
        return out;
    }
    private ObjectNode renderNeutral(ValidatedClaims validated) {
        var sections = validated.sections();
        var key = sections.get("fator_chave");
        var red = sections.get("alerta_vermelho");
        var conclusion = sections.get("veredito");
        ObjectNode out = mapper.createObjectNode();
        out.put("fator_chave", key.size() == 1 ? summary(key.getFirst())
                : "Há múltiplos recortes para descrever, sem eleger um fundamento único. " + summaries(key));
        out.put("vantagem_tatica", (key.size() == 1 ? neutralDetail(key.getFirst())
                : "Os encontros são preservados em resumo, sem ordenação de força: " + summaries(key))
                + " Nenhuma oportunidade localizada permite escolher o vencedor do jogo.");
        out.put("alerta_vermelho", red.stream().map(c -> switch (validated.relations().getOrDefault(c.id(), "LIMITATION")) {
            case "DIRECT_CONFLICT" -> "Contraponto direto ao recorte: " + (red.size() == 1 ? neutralDetail(c) : summary(c));
            case "INDEPENDENT_OPPORTUNITY" -> "Oportunidade independente do adversário, não refutação direta: " + (red.size() == 1 ? neutralDetail(c) : summary(c));
            default -> "Limitação: " + sentence(c);
        }).collect(java.util.stream.Collectors.joining(" ")));
        out.put("veredito", "O confronto permanece inconclusivo; nenhum time é escolhido. " + summaries(conclusion)
                + " Os fundamentos podem ser correlacionados e não contam como votos independentes.");
        return out;
    }
    private String summaries(List<Claim> claims) {
        return claims.stream().map(this::summary).collect(java.util.stream.Collectors.joining(" "));
    }
    private String summary(Claim c) {
        if (c.type() == Type.LIMITATION) return sentence(c);
        String foundation = switch (c.windows().getFirst().metric()) {
            case OFF_EPA_PASS -> "Passe";
            case OFF_EPA_RUSH -> "Corrida";
            default -> "Panorama por jogada";
        };
        return foundation + " de " + c.subject() + " contra a defesa de " + c.windows().get(1).team() + ": "
                + switch (c.predicate()) {
                    case POSITIVE_EPA_CONVERGENCE -> "oportunidade condicional nos sinais observados.";
                    case CONFLICTING_EPA_PROFILE -> "sinais positivos e negativos coexistem no encontro, sem direção sustentada.";
                    default -> "perfil descritivo, sem direção sustentada.";
                };
    }
    private String neutralDetail(Claim c) {
        if (c.type() == Type.LIMITATION) return sentence(c);
        String detail = sentence(c);
        if (c.predicate() == Predicate.CONFLICTING_EPA_PROFILE)
            detail += " Há sinais positivos e negativos nesse encontro; uma média isolada não resolve o conflito.";
        for (var w : c.windows()) if (w.weeks().getLast() - w.weeks().getFirst() + 1 != w.weeks().size())
            detail += " Há lacunas entre as semanas observadas de " + w.team() + "; o contexto não informa a causa.";
        if (c.windows().get(0).aggregation() != c.windows().get(1).aggregation())
            detail += " Os métodos de agregação diferem; as médias não são tratadas como recortes comparáveis.";
        return detail;
    }

    private String sentence(Claim claim) {
        if (claim.type() == Type.LIMITATION) return switch (claim.predicate()) {
            case NO_DATA -> "Não há métricas elegíveis para o confronto.";
            case HISTORICAL_ONLY -> "As métricas disponíveis são apenas referência histórica.";
            case SMALL_SAMPLE -> "Ao menos um time tem no máximo duas semanas com métricas atuais; a amostra curta limita a leitura.";
            case LIMITED_WINDOW -> "O contexto cobre no máximo três semanas elegíveis por time e não estabelece uma característica permanente.";
            case NO_MATCHUP_SUPPORT -> "Não há suporte dos dois lados para uma vantagem observada.";
            case PARTIAL_DATA -> "Faltam métricas elegíveis de um dos times; a leitura dos dois lados está incompleta.";
            case UNEVEN_WINDOWS -> "Os times têm semanas observadas diferentes; não há ajuste por adversário nesses recortes.";
            case MIXED_SIGNALS -> "Há EPA semanal positivo e negativo no mesmo recorte; a média não resume toda a variação observada.";
            default -> throw new IllegalStateException();
        };
        if (claim.type() == Type.WINDOW_COMPARISON || claim.type() == Type.MATCHUP) {
            EvidenceWindow first = claim.windows().get(0), second = claim.windows().get(1);
            String detail = windowSentence(first) + " " + windowSentence(second);
            if (claim.type() == Type.WINDOW_COMPARISON) return detail + " A média de " + first.team() + " é "
                    + (claim.predicate() == Predicate.GREATER_THAN ? "maior" : "menor")
                    + " neste recorte; os números não têm ajuste por adversário.";
            return detail + (claim.predicate() == Predicate.POSITIVE_EPA_CONVERGENCE
                    ? " O ataque produziu EPA positivo e a defesa adversária permitiu EPA positivo em cada semana observada nesse fundamento."
                    + " É uma oportunidade condicional para " + first.team() + ", sem demonstrar superioridade geral ou prever exploração no jogo."
                    : " Esse encontro entre ataque e defesa descreve o fundamento, sem demonstrar capacidade de exploração.");
        }
        Evidence first = claim.items().getFirst();
        String scope = first.origin() == Evidence.Origin.HISTORICAL_REFERENCE ? "na temporada anterior, semana " : "na temporada atual, semana ";
        if (claim.type() == Type.OBSERVATION) return claim.subject() + " registrou " + first.metric().label()
                + " de " + format(first) + " " + scope + first.week() + ".";
        Evidence second = claim.items().get(1);
        String relation = claim.predicate() == Predicate.GREATER_THAN ? "maior" : "menor";
        return claim.subject() + " registrou " + first.metric().label() + " " + relation + " que " + second.team()
                + " (" + format(first) + " contra " + format(second) + ") " + scope + first.week() + ".";
    }

    private String format(Evidence item) {
        return format(item.value(), item.unit());
    }

    private String windowSentence(EvidenceWindow window) {
        String summary = window.aggregation() == EvidenceWindow.Aggregation.PLAY_WEIGHTED_MEAN
                ? "média ponderada por " + window.volume() + " jogadas" : "média das médias semanais, sem ponderação por jogadas";
        String period = window.origin() == Evidence.Origin.HISTORICAL_REFERENCE ? "referência histórica" : "temporada atual";
        return window.team() + ": " + window.metric().label() + " de " + format(window.value(), window.metric().unit())
                + " (" + summary + "; " + period + ", semanas "
                + window.weeks().stream().map(String::valueOf).collect(java.util.stream.Collectors.joining(", "))
                + "; " + window.weeks().size() + " observações semanais; faixa "
                + format(window.minimum(), window.metric().unit()) + " a " + format(window.maximum(), window.metric().unit())
                + (window.missingMetricWeeks().isEmpty() ? "" : "; métrica ausente nas semanas " + window.missingMetricWeeks())
                + ").";
    }

    private String format(java.math.BigDecimal value, MetricCatalog.Unit unit) {
        DecimalFormatSymbols symbols = DecimalFormatSymbols.getInstance(Locale.forLanguageTag("pt-BR"));
        DecimalFormat formatter = new DecimalFormat(unit == MetricCatalog.Unit.EPA ? "+0.000;-0.000" : "0.0", symbols);
        formatter.setRoundingMode(RoundingMode.HALF_UP);
        return formatter.format(unit == MetricCatalog.Unit.EPA ? value : value.multiply(java.math.BigDecimal.valueOf(100)))
                + (unit == MetricCatalog.Unit.RATE ? "%" : " EPA");
    }

}
