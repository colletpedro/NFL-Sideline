package com.nflsideline.coreapi.editorial.local;

import com.fasterxml.jackson.databind.*;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.nflsideline.coreapi.editorial.*;
import java.util.*;

/** Offline allowlist. Derived windows are rebuilt; arbitrary source fields are never copied to artifacts. */
public final class FrozenContext {
    private FrozenContext() { }
    public static final ObjectMapper MAPPER = new ObjectMapper().enable(DeserializationFeature.USE_BIG_DECIMAL_FOR_FLOATS)
            .enable(DeserializationFeature.FAIL_ON_TRAILING_TOKENS);
    public static EditorialParameters parameters(AnalysisContext context) {
        try {
            var game = MAPPER.readTree(context.canonicalJson()).path("game");
            return new EditorialParameters(game.path("season").asInt(), game.path("week").asInt(), game.path("phase").asText());
        } catch (java.io.IOException failure) { throw new IllegalArgumentException("Invalid calendar"); }
    }
    public static AnalysisContext read(JsonNode root) throws java.io.IOException {
        if (!root.path("contract_version").isIntegralNumber() || root.path("contract_version").asInt() != 3
                || !root.path("evidence").isArray()) throw new IllegalArgumentException("Invalid frozen context");
        var evidence = new TreeMap<String, Evidence>();
        for (var item : root.path("evidence")) {
            Evidence e = MAPPER.treeToValue(item, Evidence.class);
            Evidence previous = evidence.putIfAbsent(e.id(), e);
            if (previous != null && !previous.equals(e)) throw new IllegalArgumentException("Conflicting evidence");
        }
        ObjectNode sanitized = MAPPER.createObjectNode().put("contract_version", 3);
        var game = sanitized.putObject("game");
        String gameId = root.path("game").path("game_id").asText();
        if (!gameId.matches("[A-Za-z0-9_-]+")) throw new IllegalArgumentException("Invalid game id");
        game.put("game_id", gameId).put("season", root.path("game").path("season").asInt())
                .put("week", root.path("game").path("week").asInt()).put("phase", root.path("game").path("phase").asText());
        sanitized.put("home_team", root.path("home_team").asText()).put("away_team", root.path("away_team").asText());
        var values = List.copyOf(evidence.values());
        boolean home = values.stream().anyMatch(e -> e.team().equals(root.path("home_team").asText()));
        boolean away = values.stream().anyMatch(e -> e.team().equals(root.path("away_team").asText()));
        ContextQuality quality = values.isEmpty() ? ContextQuality.MINIMAL
                : home && away && values.stream().allMatch(e -> e.origin() == Evidence.Origin.CURRENT_SEASON_PRIOR_WEEKS)
                ? ContextQuality.COMPLETE : ContextQuality.PARTIAL;
        sanitized.put("data_coverage", quality.name());
        sanitized.set("evidence", MAPPER.valueToTree(values));
        sanitized.set("recent_windows", MAPPER.valueToTree(EvidenceWindow.from(values)));
        var context = new AnalysisContext(MAPPER.writeValueAsString(sanitized), quality, values,
                sanitized.path("home_team").asText(), sanitized.path("away_team").asText());
        check(context, parameters(context));
        return context;
    }
    public static void check(AnalysisContext context, EditorialParameters p) {
        if (!context.homeTeam().matches("[A-Z0-9]{1,5}") || !context.awayTeam().matches("[A-Z0-9]{1,5}")
                || context.homeTeam().equals(context.awayTeam()) || !Set.of("REG", "POST", "WC", "DIV", "CON", "SB").contains(p.phase()))
            throw new IllegalArgumentException("Invalid teams or phase");
        for (var e : context.evidence()) {
            boolean current = e.origin() == Evidence.Origin.CURRENT_SEASON_PRIOR_WEEKS;
            if (!List.of(context.homeTeam(), context.awayTeam()).contains(e.team()) || e.value() == null || e.metric() == null
                    || e.origin() == null || e.unit() != e.metric().unit() || e.week() < 1 || e.week() > 30
                    || !"team_week_metrics".equals(e.sourceTable())
                    || !(e.season() + ":" + e.week() + ":" + e.team()).equals(e.sourceKey())
                    || !Evidence.observed(e.team(), e.metric(), e.season(), e.week(), !current, e.value(), e.volume()).id().equals(e.id())
                    || current && (!p.phase().equals("REG") || e.season() != p.season() || e.week() >= p.gameWeek())
                    || !current && e.season() != p.season() - 1)
                throw new IllegalArgumentException("Invalid frozen evidence");
        }
        for (String team : List.of(context.homeTeam(), context.awayTeam())) {
            var items = context.evidence().stream().filter(e -> e.team().equals(team)).toList();
            if (items.stream().map(Evidence::week).distinct().count() > 3
                    || items.stream().map(Evidence::origin).distinct().count() > 1)
                throw new IllegalArgumentException("Frozen slice exceeds policy");
        }
    }
}
