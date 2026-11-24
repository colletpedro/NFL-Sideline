package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.nflsideline.coreapi.editorial.local.MatchupAssessment;
import java.math.*;
import java.text.*;
import java.util.*;
import java.util.stream.Collectors;
import static com.nflsideline.coreapi.editorial.ClaimSelection.*;
import static com.nflsideline.coreapi.editorial.SignalClaimValidator.Resolved;

/** Controlled v5 prose. Receives only resolved, mechanically validated facts. */
final class SignalClaimRenderer {
    private final ObjectMapper mapper;
    SignalClaimRenderer(ObjectMapper mapper) { this.mapper = mapper; }
    ObjectNode render(SignalClaimValidator.Validated validated) {
        var key = validated.sections.get("fator_chave");
        var red = validated.sections.get("alerta_vermelho");
        var verdict = validated.sections.get("veredito");
        ObjectNode out = mapper.createObjectNode();
        var main = key.stream().filter(r -> r.candidate() != null).map(Resolved::candidate).toList();
        out.put("fator_chave", main.isEmpty() ? "Faltam recortes compatíveis para descrever os encontros de ataque e defesa."
                : headlines(main));
        out.put("vantagem_tatica", main.isEmpty() ? global(key.getFirst().claim().predicate())
                : numericalDetails(main));
        // Group identical internal conditions without discarding their links or affected foundations.
        var internal = new LinkedHashMap<Predicate, List<Resolved>>();
        var alerts = new ArrayList<String>();
        for (var r : red) {
            if (r.claim().type() == Kind.WINDOW_LIMITATION) internal.computeIfAbsent(r.claim().predicate(), k -> new ArrayList<>()).add(r);
            else if (r.claim().type() == Kind.LIMITATION) alerts.add(globalAlert(r.claim().predicate()));
            else {
                var c = r.candidate();
                String lead = validated.relations.get(r.claim().id()) == Relation.INDEPENDENT_OPPORTUNITY
                        ? "Há também uma oportunidade independente do adversário: "
                        : "A leitura não se estende automaticamente a outro fundamento: ";
                alerts.add(lead + numericalDetails(List.of(c)));
            }
        }
        internal.forEach((predicate, items) -> alerts.add(internalLimit(predicate, items)));
        out.put("alerta_vermelho", String.join(" ", alerts));
        out.put("veredito", conclusion(verdict));
        return out;
    }
    private String headlines(List<MatchupAssessment.Candidate> main) {
        var groups = new LinkedHashMap<String, List<MatchupAssessment.Candidate>>();
        for (var c : main) groups.computeIfAbsent(c.attackTeam() + ":" + c.signals().relation(), k -> new ArrayList<>()).add(c);
        return groups.values().stream().map(items -> {
            var first = items.getFirst();
            String single = foundation(first) + " de " + first.attackTeam();
            String combined = join(items.stream().map(this::foundation).toList()) + " de " + first.attackTeam();
            return headline(first).replace(single, combined);
        }).collect(Collectors.joining(" "));
    }
    private String headline(MatchupAssessment.Candidate c) {
        String name = foundation(c) + " de " + c.attackTeam() + " contra " + c.defenseTeam();
        return name + switch (c.signals().relation()) {
            case POSITIVE_CONVERGENCE -> ": sinais compatíveis com uma oportunidade localizada.";
            case FAVORABLE_ATTACK_AND_DEFENSE -> ": indicadores favoráveis ao ataque e à defesa.";
            case ATTACK_NOT_DEMONSTRATED -> ": produção ofensiva positiva não demonstrada no recorte.";
            case BOTH_NEGATIVE -> ": EPA negativo no ataque de " + c.attackTeam() + " e no permitido pela defesa de " + c.defenseTeam() + ".";
            case WEEKLY_SIGN_VARIATION -> ": há semanas com EPA positivo e negativo no recorte.";
            case ZERO_PROFILE -> ": há semanas com EPA zero.";
            case POSITIVE_COMPATIBILITY_ONLY -> ": sinais positivos com cobertura limitada.";
            default -> ": faltam recortes compatíveis.";
        };
    }
    private String numericalDetails(List<MatchupAssessment.Candidate> candidates) {
        var windows = candidates.stream().flatMap(c -> java.util.stream.Stream.of(c.attack(), c.defense())).toList();
        boolean sharedScope = windows.stream().map(this::scope).distinct().count() == 1;
        boolean sharedAggregation = windows.stream().map(EvidenceWindow::aggregation).distinct().count() == 1;
        String prefix = sharedScope ? scope(windows.getFirst()) + ". " : "";
        if (sharedAggregation) prefix += windows.getFirst().aggregation() == EvidenceWindow.Aggregation.MEAN_OF_WEEKLY_MEANS
                ? "Médias das médias semanais, sem ponderação por jogadas. "
                : "Médias ponderadas pelos volumes de jogadas indicados. ";
        boolean sharedInterpretation = candidates.size() > 1 && candidates.stream().map(this::interpretation).distinct().count() == 1;
        var rows = new ArrayList<String>();
        for (var c : candidates) {
            rows.add(foundation(c) + " — " + c.attackTeam() + " (ataque): " + number(c.attack(), sharedScope, sharedAggregation)
                    + "; " + c.defenseTeam() + " (EPA permitido): " + number(c.defense(), sharedScope, sharedAggregation)
                    + "." + (sharedInterpretation ? "" : " " + interpretation(c)));
        }
        return prefix.stripTrailing() + "\n" + String.join("\n", rows)
                + (sharedInterpretation ? "\nEm cada encontro descrito: " + interpretation(candidates.getFirst()) : "");
    }
    private String number(EvidenceWindow w, boolean sharedScope, boolean sharedAggregation) {
        String text = format(w.value());
        if (w.minimum().compareTo(w.maximum()) != 0) {
            // An inequality describes one endpoint; never concatenate it as a scalar in “x a y”.
            if (belowDisplayResolution(w.minimum()) || belowDisplayResolution(w.maximum()))
                text += ", faixa semanal: mínimo (" + format(w.minimum()) + "); máximo (" + format(w.maximum()) + ")";
            else text += ", faixa semanal de " + format(w.minimum()) + " a " + format(w.maximum());
        }
        if (!sharedScope) text += ", " + scope(w);
        if (w.aggregation() == EvidenceWindow.Aggregation.PLAY_WEIGHTED_MEAN) text += ", " + w.volume() + " jogadas"
                + (sharedAggregation ? "" : ", média ponderada");
        else if (!sharedAggregation) text += ", média das médias semanais sem ponderação por jogadas";
        if (!w.missingMetricWeeks().isEmpty()) text += ", métrica ausente nas semanas " + weeks(w.missingMetricWeeks());
        return text;
    }
    private String interpretation(MatchupAssessment.Candidate c) {
        return switch (c.signals().relation()) {
            case POSITIVE_CONVERGENCE -> "O ataque produziu EPA positivo e a defesa permitiu EPA positivo em todas as semanas do recorte; a compatibilidade não demonstra exploração no jogo.";
            case FAVORABLE_ATTACK_AND_DEFENSE -> "Ataque positivo e EPA permitido negativo em todas as semanas: indicadores favoráveis a ambos, sem estabelecer quem prevalecerá.";
            case ATTACK_NOT_DEMONSTRATED -> "A defesa permitiu EPA positivo em todas as semanas, mas o ataque teve EPA negativo em todas; não demonstrou produção positiva para sustentar exploração.";
            case BOTH_NEGATIVE -> "O ataque produziu EPA negativo e a defesa permitiu EPA negativo em todas as semanas; isso não projeta o resultado do encontro.";
            case POSITIVE_COMPATIBILITY_ONLY -> "Os valores são positivos nas semanas disponíveis, mas a cobertura não autoriza reconhecer uma oportunidade atual.";
            default -> "Ataque: " + signDescription(c.signals().attack()) + ". Defesa, em EPA permitido: " + signDescription(c.signals().defense()) + ".";
        };
    }
    private String signDescription(SignalDimensions.Weekly weekly) {
        return switch (weekly.pattern()) {
            case ALL_POSITIVE -> "positivo em todas as semanas";
            case ALL_NEGATIVE -> "negativo em todas as semanas";
            case MIXED_SIGNS -> "semanas positivas e negativas" + (weekly.containsZero() ? ", além de EPA zero" : "");
            case NONNEGATIVE_WITH_ZERO -> "semanas positivas e semanas com EPA zero";
            case NONPOSITIVE_WITH_ZERO -> "semanas negativas e semanas com EPA zero";
            case ZERO_ONLY -> "EPA zero em todas as semanas";
            case MISSING -> "sem observações";
        };
    }
    private String internalLimit(Predicate predicate, List<Resolved> items) {
        var affected = new LinkedHashMap<String, List<String>>();
        items.forEach(r -> affected.computeIfAbsent(r.candidate().attackTeam(), k -> new ArrayList<>())
                .add(foundation(r.candidate()).toLowerCase(Locale.ROOT)));
        String subjects = join(affected.entrySet().stream().map(e -> join(e.getValue()) + " de " + e.getKey()).toList());
        return switch (predicate) {
            case SIGN_VARIATION_LIMIT -> {
                var varying = new LinkedHashMap<String, List<String>>();
                for (var r : items) {
                    var c = r.candidate();
                    if (c.signals().attack().pattern() == SignalDimensions.Pattern.MIXED_SIGNS)
                        varying.computeIfAbsent("ataque de " + c.attackTeam(), k -> new ArrayList<>()).add(foundation(c).toLowerCase(Locale.ROOT));
                    if (c.signals().defense().pattern() == SignalDimensions.Pattern.MIXED_SIGNS)
                        varying.computeIfAbsent("EPA permitido pela defesa de " + c.defenseTeam(), k -> new ArrayList<>()).add(foundation(c).toLowerCase(Locale.ROOT));
                }
                yield "As médias " + join(varying.entrySet().stream().map(e -> "do " + e.getKey() + " (" + join(e.getValue()) + ")").toList()) + " combinam semanas de sinais diferentes; não descrevem um sinal presente em todas elas.";
            }
            case SAMPLE_LIMIT -> "Nos recortes de " + subjects + ", há no máximo duas observações semanais por métrica; o recorte curto não estabelece um padrão duradouro.";
            case COVERAGE_LIMIT -> {
                var reasons = new LinkedHashSet<String>();
                for (var r : items) {
                    var c = r.candidate();
                    if (!c.current()) reasons.add("as referências são históricas");
                    if (c.limitations().contains(MatchupAssessment.Limitation.DIFFERENT_WEEKS)) reasons.add("as equipes têm semanas observadas diferentes");
                    if (c.limitations().contains(MatchupAssessment.Limitation.MISSING_METRIC_WEEKS)) reasons.add("há métricas ausentes em semanas representadas");
                    if (c.limitations().contains(MatchupAssessment.Limitation.NOT_RECENT_COMPLETE)) reasons.add("não estão cobertas todas as semanas numéricas imediatamente anteriores");
                    if (c.limitations().contains(MatchupAssessment.Limitation.DIFFERENT_AGGREGATION)) reasons.add("os métodos de agregação diferem");
                }
                yield "Em " + subjects + ", " + String.join("; ", reasons) + ". Essas diferenças limitam uma leitura conjunta do momento atual; a causa de eventuais lacunas não está informada.";
            }
            default -> "Os recortes de " + subjects + " cobrem até três semanas e não têm ajuste por adversário; não estabelecem uma característica permanente.";
        };
    }
    private String conclusion(List<Resolved> claims) {
        var teams = new TreeMap<String, List<MatchupAssessment.Candidate>>();
        for (var r : claims) if (r.claim().type() == Kind.MATCHUP)
            teams.computeIfAbsent(r.candidate().attackTeam(), k -> new ArrayList<>()).add(r.candidate());
        var parts = new ArrayList<String>();
        teams.forEach((team, candidates) -> {
            var groups = new LinkedHashMap<String, List<MatchupAssessment.Candidate>>();
            for (var c : candidates) groups.computeIfAbsent(c.signals().relation() + ":" + c.signals().attack().pattern()
                    + ":" + c.signals().defense().pattern() + ":" + c.signals().attack().containsZero()
                    + ":" + c.signals().defense().containsZero(), k -> new ArrayList<>()).add(c);
            groups.forEach((signature, matched) -> {
                var c = matched.getFirst();
                String scope = "No recorte de " + join(matched.stream().map(m -> foundation(m).toLowerCase(Locale.ROOT)).toList())
                        + " do ataque de " + c.attackTeam() + " contra a defesa de " + c.defenseTeam();
                String description = switch (c.signals().relation()) {
                    case POSITIVE_CONVERGENCE -> "há uma oportunidade localizada, com EPA ofensivo e permitido positivos nas semanas observadas";
                    case FAVORABLE_ATTACK_AND_DEFENSE -> "o ataque de " + c.attackTeam() + " teve EPA positivo e a defesa de " + c.defenseTeam()
                            + " permitiu EPA negativo nas semanas observadas; indicadores favoráveis a ambos, sem indicar quem prevalecerá";
                    case ATTACK_NOT_DEMONSTRATED -> "o ataque de " + c.attackTeam() + " não mostrou EPA positivo, apesar do EPA positivo permitido pela defesa de " + c.defenseTeam();
                    case BOTH_NEGATIVE -> "o ataque de " + c.attackTeam() + " apresentou EPA negativo e a defesa de " + c.defenseTeam() + " permitiu EPA negativo nas semanas observadas";
                    case WEEKLY_SIGN_VARIATION, ZERO_PROFILE -> variationSummary(c);
                    case POSITIVE_COMPATIBILITY_ONLY -> "o ataque de " + c.attackTeam() + " teve EPA positivo e a defesa de " + c.defenseTeam()
                            + " permitiu EPA positivo nas semanas disponíveis, sem cobertura para oportunidade atual";
                    default -> "faltam dados compatíveis";
                };
                parts.add(scope + (matched.stream().allMatch(m -> !m.current()) ? " (referência histórica)" : "") + ", " + description + ".");
            });
        });
        if (teams.isEmpty()) parts.add("Os dados não permitem compor os encontros de ataque e defesa.");
        // Restrictions are summarized, not a second listing of claims or correlated opportunities.
        var predicates = claims.stream().map(r -> r.claim().predicate()).collect(Collectors.toSet());
        if (predicates.contains(Predicate.COVERAGE_LIMIT) || predicates.contains(Predicate.UNEVEN_WINDOWS))
            parts.add("As diferenças de cobertura restringem a leitura conjunta.");
        else if (predicates.contains(Predicate.SMALL_SAMPLE) || predicates.contains(Predicate.SAMPLE_LIMIT))
            parts.add("A leitura se limita a um recorte curto.");
        else parts.add("A leitura se limita às semanas observadas.");
        parts.add("Esta análise descritiva não estima o vencedor.");
        return String.join(" ", parts);
    }
    private String variationSummary(MatchupAssessment.Candidate c) {
        return "no EPA do ataque de " + c.attackTeam() + ", há " + weeklyObservations(c.signals().attack())
                + "; no EPA permitido pela defesa de " + c.defenseTeam() + ", há " + weeklyObservations(c.signals().defense());
    }
    private String weeklyObservations(SignalDimensions.Weekly weekly) {
        return switch (weekly.pattern()) {
            case ALL_POSITIVE -> "valores positivos em todas as semanas observadas";
            case ALL_NEGATIVE -> "valores negativos em todas as semanas observadas";
            case MIXED_SIGNS -> "semanas com valores positivos e negativos" + (weekly.containsZero() ? ", além de zero" : "");
            case NONNEGATIVE_WITH_ZERO -> "semanas com valores positivos e semanas com zero";
            case NONPOSITIVE_WITH_ZERO -> "semanas com valores negativos e semanas com zero";
            case ZERO_ONLY -> "zero em todas as semanas observadas";
            case MISSING -> "ausência de observações";
        };
    }

    private String join(List<String> items) {
        if (items.size() < 2) return items.isEmpty() ? "" : items.getFirst();
        return String.join(", ", items.subList(0, items.size() - 1)) + " e " + items.getLast();
    }
    private String global(Predicate p) {
        return switch (p) {
            case NO_DATA -> "Não há métricas elegíveis para o confronto.";
            case PARTIAL_DATA -> "Faltam métricas elegíveis de um dos times.";
            case HISTORICAL_ONLY -> "As métricas disponíveis são apenas referência histórica.";
            case UNEVEN_WINDOWS -> "Os times têm semanas observadas diferentes.";
            case SMALL_SAMPLE -> "Ao menos um time tem no máximo duas semanas atuais observadas.";
            default -> "O contexto cobre no máximo três semanas por time.";
        };
    }
    private String globalAlert(Predicate p) {
        return switch (p) {
            case NO_DATA, PARTIAL_DATA -> "Sem evidências pareadas, não é possível confrontar a produção de um ataque com o EPA permitido pela defesa adversária.";
            case HISTORICAL_ONLY -> "Referências históricas não descrevem o momento atual das equipes.";
            default -> "A cobertura disponível não sustenta extrapolar os recortes para o jogo.";
        };
    }
    private String foundation(MatchupAssessment.Candidate c) {
        return switch (c.foundation()) { case OFF_EPA_PASS -> "Passe"; case OFF_EPA_RUSH -> "Corrida"; default -> "Panorama por jogada"; };
    }
    private String scope(EvidenceWindow w) {
        return (w.origin() == Evidence.Origin.HISTORICAL_REFERENCE ? "Referência histórica " : "Temporada ")
                + w.season() + ", semanas " + weeks(w.weeks()) + " (" + w.weeks().size() + " observações por métrica)";
    }
    private String weeks(List<Integer> weeks) { return weeks.stream().map(String::valueOf).collect(Collectors.joining(", ")); }
    private boolean belowDisplayResolution(BigDecimal value) {
        return value.signum() != 0 && value.setScale(3, RoundingMode.HALF_UP).signum() == 0;
    }
    private String format(BigDecimal value) {
        if (belowDisplayResolution(value))
            return value.signum() > 0 ? "0 < EPA < 0,0005" : "-0,0005 < EPA < 0";
        var f = new DecimalFormat(value.signum() == 0 ? "0.000" : "+0.000;-0.000",
                DecimalFormatSymbols.getInstance(Locale.forLanguageTag("pt-BR")));
        f.setRoundingMode(RoundingMode.HALF_UP);
        return f.format(value) + " EPA";
    }
}
