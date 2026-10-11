package com.nflsideline.coreapi.metrics.temporal;

import java.io.IOException;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.LinkOption;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Base64;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import static com.nflsideline.coreapi.metrics.temporal.TemporalValue.*;

/** Pure result-v2 contract/integrity reader. Does not run the temporal algorithm. */
public final class TemporalResultReader {
    private static final Set<String> SEMANTIC = Set.of("resultVersion", "algorithmVersion", "policy", "request",
        "asOfDateMapping", "pregame", "blocks", "resourcesUsed", "calculationsUsed", "evidenceUsed");
    private static final Set<String> AUDIT = Set.of("result_id", "derivedAt", "structuralValidation", "revisionDecisions",
        "temporalEligibility", "input_id", "resourceDecisions", "evidenceQualifications", "guarantees", "audit_id");
    private static final List<String> COUNTS = List.of("eligible_n", "epa_n", "success_n", "epa_missing_n", "epa_nonfinite_n");
    public TemporalResult read(Path root) throws IOException {
        Path absolute = root.toAbsolutePath().normalize();
        for (Path p = absolute; p != null; p = p.getParent()) check(!Files.isSymbolicLink(p), "Symlink path forbidden");
        var marker = object(PythonJson.parse(readFile(absolute.resolve("COMPLETED.json"))));
        fields(marker, Set.of("resultVersion", "result_id", "audit_id", "files"));
        check(marker.text("resultVersion").equals("metrics-temporal-result-v2"), "Unsupported result version (v1 refused)");
        fields(marker.object("files"), Set.of("result.json"));
        byte[] bytes = readFile(absolute.resolve("result.json"));
        check(PythonJson.sha(bytes).equals(marker.object("files").text("result.json")), "Result byte hash mismatch");
        var document = object(PythonJson.parse(bytes));
        check(document.text("result_id").equals(marker.text("result_id")) &&
              document.text("audit_id").equals(marker.text("audit_id")), "Marker identity binding mismatch");
        return validate(document);
    }
    private static byte[] readFile(Path path) throws IOException {
        check(Files.isRegularFile(path, LinkOption.NOFOLLOW_LINKS) && !Files.isSymbolicLink(path), "Regular artifact file required");
        return Files.readAllBytes(path);
    }
    public TemporalResult validate(ObjectValue d) {
        var rootKeys = new HashSet<>(SEMANTIC); rootKeys.addAll(AUDIT); fields(d, rootKeys);
        check(d.text("resultVersion").equals("metrics-temporal-result-v2"), "Unsupported result version (v1 refused)");
        check(d.text("algorithmVersion").equals("metrics-temporal-1.0.1"), "Unsupported algorithm version");
        check(d.text("structuralValidation").equals("PASSED"), "Unvalidated temporal artifact");
        var semantic = new HashMap<String, TemporalValue>();
        for (var key : SEMANTIC) semantic.put(key, d.get(key));
        check(PythonJson.identity(new ObjectValue(semantic)).equals(d.text("result_id")), "Semantic result_id mismatch");
        check(PythonJson.identity(d.without("audit_id")).equals(d.text("audit_id")), "Semantic audit_id mismatch");
        id(d.text("input_id")); id(d.text("result_id")); id(d.text("audit_id"));
        ExactInstant.epochSeconds(d.text("derivedAt"));
        var request = d.object("request");
        var required = Set.of("season", "phase", "team", "targetGameId", "targetWeek", "mode", "windows", "asOfInstant");
        fields(request, required, Set.of("week", "historicalSeason", "historicalPhase"));
        check(Set.of("POINT_IN_TIME", "EVENT_RECONSTRUCTION").contains(request.text("mode")), "Invalid temporal mode");
        check(Set.of("REG", "POST").contains(request.text("phase")), "Invalid phase");
        nonnegative(request.integer("season")); nonnegative(request.integer("targetWeek"));
        text(request.text("team")); text(request.text("targetGameId"));
        var cut = ExactInstant.epochSeconds(request.text("asOfInstant"));
        check(cut.scale() <= 0 && request.text("asOfInstant").endsWith("Z"), "Normalized whole-second UTC cutoff required");
        var guarantees = d.object("guarantees");
        fields(guarantees, Set.of("temporalMode", "knowledgeAtCutoff", "historicalAvailability", "laterKnowledgePermitted",
            "postCutoffEvidenceIds", "postCutoffResourceIds", "unknownKnowledgeResourceIds", "statisticalUncertainty", "limits"));
        boolean retro = request.text("mode").equals("EVENT_RECONSTRUCTION");
        check(guarantees.text("temporalMode").equals(request.text("mode")) && guarantees.bool("laterKnowledgePermitted") == retro,
              "Mode and guarantees disagree");
        check(guarantees.text("knowledgeAtCutoff").equals(retro ? "NOT_DEMONSTRATED" : "CONDITIONAL_ON_MATERIALIZED_POLICY_EVIDENCE"), "Invalid knowledge guarantee");
        check(guarantees.text("historicalAvailability").equals(retro ? "UNKNOWN_OR_NOT_PROVEN" : "ONLY_SELECTED_SOURCES_PROVEN_BY_POLICY"), "Invalid availability guarantee");
        check(guarantees.text("statisticalUncertainty").equals("NOT_ESTIMATED"), "Unsupported uncertainty assertion");
        var resources = index(d.array("resourcesUsed"), "revision_id");
        var calculations = index(d.array("calculationsUsed"), "revision_id");
        var evidence = index(d.array("evidenceUsed"), "evidence_id");
        for (var r : resources.values()) resource(r, resources);
        for (var e : evidence.values()) {
            fields(e, Set.of("evidence_id", "kind", "subject_id", "origin", "reference", "recorded_at", "value", "dependencies"), Set.of("receipt"));
            text(e.text("subject_id")); text(e.text("origin")); text(e.text("reference"));
            ExactInstant.epochSeconds(e.text("recorded_at"));
            for (var dependency : strings(e.array("dependencies"))) check(resources.containsKey(dependency), "Unresolved used evidence dependency");
            if (e.fields().containsKey("receipt")) receipt(e.object("receipt"), e);
        }
        for (var c : calculations.values()) calculation(c, resources);
        var blocks = new ArrayList<TemporalResult.Block>();
        for (var value : d.array("blocks")) {
            var b = object(value);
            fields(b, Set.of("window", "origin", "season", "phase", "calendarRevisionId", "requestedWeeks", "actualWeeks",
                "scheduledGameIds", "events", "coverage", "weeklyStates", "aggregates", "requestedPeriod"));
            requestedPeriod(b, request);
            if (!b.isNull("calendarRevisionId")) check(resources.containsKey(b.text("calendarRevisionId")) &&
                resources.get(b.text("calendarRevisionId")).text("kind").equals("CALENDAR"), "Block/calendar binding mismatch");
            var coverage = b.object("coverage");
            fields(coverage, Set.of("expectedGames", "expectationFailures", "availabilityKnownGameIds", "metricObservedGameIds",
                "knownEligibleGameIds", "outsideCutoffGameIds", "uncertainGameIds", "observedGameIds", "observedCompleteGameIds",
                "sourceRatio", "calendarComplete", "closedWeeks", "gaps"));
            if (coverage.isNull("expectedGames")) check(coverage.isNull("sourceRatio"), "UNKNOWN expectation must preserve null ratio");
            else {
                nonnegative(coverage.integer("expectedGames"));
                check(coverage.integer("expectedGames").equals(BigInteger.valueOf(coverage.array("knownEligibleGameIds").size())), "Expected/eligible count mismatch");
                ratio(coverage.get("sourceRatio"), new BigDecimal(coverage.array("observedCompleteGameIds").size()), coverage.integer("expectedGames"));
            }
            var events = index(b.array("events"), "game", true);
            for (var event : events.values()) {
                var game = event.object("game"); game(game);
                if (!event.isNull("calculationRevisionId")) {
                    var c = calculations.get(event.text("calculationRevisionId"));
                    check(c != null && c.object("game").equals(game) &&
                        c.text("calculation_id").equals(event.text("calculationId")) &&
                        c.text("coverage_revision_id").equals(event.text("coverageRevisionId")) &&
                        c.text("pbp_revision_id").equals(event.text("sourceSetId")), "Event/calculation identity mismatch");
                    check(!game.text("game_id").equals(request.text("targetGameId")), "Target cannot contribute statistics");
                } else check(event.isNull("calculationId") && event.isNull("coverageRevisionId") && event.isNull("sourceSetId"), "Partial event association");
                if (!event.isNull("stateRevisionId")) {
                    var state = resources.get(event.text("stateRevisionId"));
                    check(state != null && state.text("kind").equals("STATE") && state.object("payload").text("game_id").equals(game.text("game_id")), "Event/state mismatch");
                }
            }
            var aggregates = new ArrayList<TemporalResult.Aggregate>();
            var byGroup = new HashMap<String, ObjectValue>();
            for (var aValue : b.array("aggregates")) {
                var a = object(aValue);
                fields(a, Set.of("scope", "model", "role", "foundation", "populationVersion", "definitionVersion", "gameIds", "sums",
                    "volume", "epa", "successRate", "frequency", "foundationCoverage", "comparisonEligible", "comparisonFailures", "statisticalUncertainty"));
                check(Set.of("COMPLETE", "AUDITABLE_SUBSET_UNKNOWN", "AUDITABLE_SUBSET_PARTIAL").contains(a.text("scope")), "Invalid aggregate scope");
                group(a.text("role"), a.text("foundation")); text(a.text("model")); versions(a.text("populationVersion"), a.text("definitionVersion"));
                check(byGroup.put(a.text("scope") + "/" + a.text("model") + "/" + a.text("role") + "/" + a.text("foundation"), a) == null, "Duplicate aggregate group");
                var s = sums(a.object("sums"));
                reconcileAggregate(a, events, calculations, request.text("team"), s);
                var fc = a.object("foundationCoverage");
                fields(fc, Set.of("observedSourceGames", "expectedGames", "eligibleN", "epaN", "epaObservedGameIds",
                    "noEligiblePlaysGameIds", "noEpaObservationsGameIds", "sourceRatio"));
                check(fc.integer("observedSourceGames").equals(BigInteger.valueOf(a.array("gameIds").size())) &&
                    fc.get("expectedGames").equals(coverage.get("expectedGames")) && fc.integer("eligibleN").equals(s.eligibleN()) &&
                    fc.integer("epaN").equals(s.epaN()), "Foundation coverage count mismatch");
                if (a.text("scope").equals("COMPLETE") && !coverage.isNull("expectedGames"))
                    ratio(fc.get("sourceRatio"), new BigDecimal(a.array("gameIds").size()), coverage.integer("expectedGames"));
                else check(fc.isNull("sourceRatio"), "Unknown/subset foundation source ratio must be null");
                check(a.integer("volume").equals(s.eligibleN()), "Volume and sums disagree");
                var epa = ratio(a.get("epa"), s.epaSum(), s.epaN());
                var sr = ratio(a.get("successRate"), new BigDecimal(s.successN()), s.epaN());
                check(a.text("statisticalUncertainty").equals("NOT_ESTIMATED"), "Uncertainty must remain explicit");
                check(a.bool("comparisonEligible") == a.array("comparisonFailures").isEmpty(), "Comparison eligibility mismatch");
                for (var gid : strings(a.array("gameIds"))) check(events.containsKey(gid) && !events.get(gid).isNull("calculationRevisionId"), "Aggregate source game unresolved");
                aggregates.add(new TemporalResult.Aggregate(a, s, epa, sr, null));
            }
            var completed = new ArrayList<TemporalResult.Aggregate>();
            for (var a : aggregates) {
                var node = a.document();
                var general = byGroup.get(node.text("scope") + "/" + node.text("model") + "/" + node.text("role") + "/general");
                check(general != null && general.get("gameIds").equals(node.get("gameIds")), "Frequency/general game set mismatch");
                var freq = node.text("foundation").equals("general") ? null : ratio(node.get("frequency"), new BigDecimal(a.sums().eligibleN()), general.object("sums").integer("eligible_n"));
                if (node.text("foundation").equals("general")) {
                    check(node.isNull("frequency"), "General has no classified frequency");
                    reconcile(node.object("sums"), requiredGroup(byGroup, node, "classified_pass").object("sums"),
                        requiredGroup(byGroup, node, "classified_rush").object("sums"));
                }
                completed.add(new TemporalResult.Aggregate(node, a.sums(), a.epa(), a.successRate(), freq));
            }
            blocks.add(new TemporalResult.Block(b, completed));
        }
        return new TemporalResult(d, blocks);
    }
    private static ObjectValue requiredGroup(Map<String, ObjectValue> groups, ObjectValue a, String foundation) {
        var row = groups.get(a.text("scope") + "/" + a.text("model") + "/" + a.text("role") + "/" + foundation);
        check(row != null, "Missing classified aggregate group"); return row;
    }
    private static void reconcileAggregate(ObjectValue a, Map<String, ObjectValue> events,
            Map<String, ObjectValue> calculations, String team, TemporalResult.Sums sums) {
        var totals = new HashMap<String, BigInteger>(); for (var key : COUNTS) totals.put(key, BigInteger.ZERO);
        BigDecimal totalSum = BigDecimal.ZERO;
        var gids = strings(a.array("gameIds")); check(new HashSet<>(gids).size() == gids.size() && !gids.isEmpty(), "Aggregate game IDs must be unique and nonempty");
        var withEpa = new HashSet<String>(); var noEligible = new HashSet<String>(); var noEpa = new HashSet<String>();
        for (var gid : gids) {
            var e = events.get(gid); check(e != null && !e.isNull("calculationRevisionId"), "Aggregate source game unresolved");
            var c = calculations.get(e.text("calculationRevisionId"));
            check(c != null, "Aggregate calculation unresolved");
            var scope = e.text("completeness").equals("COMPLETE") ? "COMPLETE" : "AUDITABLE_SUBSET_" + e.text("completeness");
            check(a.text("scope").equals(scope) && a.text("model").equals(e.text("epaModel")), "Aggregate scope/model association mismatch");
            ObjectValue source = null;
            for (var rv : c.array("statistics")) {var r=object(rv); if (r.text("team").equals(team) && r.text("role").equals(a.text("role")) && r.text("foundation").equals(a.text("foundation"))) source=r;}
            check(source != null, "Aggregate sufficient source absent");
            for (var key : COUNTS) totals.put(key, totals.get(key).add(source.integer(key)));
            if (!source.isNull("epa_sum")) totalSum = totalSum.add(decimal(source.text("epa_sum")));
            if (source.integer("epa_n").signum()>0) withEpa.add(gid);
            if (source.integer("eligible_n").signum()==0) noEligible.add(gid);
            if (source.integer("eligible_n").signum()>0 && source.integer("epa_n").signum()==0) noEpa.add(gid);
        }
        for (var key : COUNTS) check(a.object("sums").integer(key).equals(totals.get(key)), "Aggregate and calculation counts diverge");
        if (sums.epaN().signum()>0) check(sums.epaSum().compareTo(totalSum)==0, "Aggregate and calculation EPA sums diverge");
        var fc = a.object("foundationCoverage");
        check(new HashSet<>(strings(fc.array("epaObservedGameIds"))).equals(withEpa) &&
            new HashSet<>(strings(fc.array("noEligiblePlaysGameIds"))).equals(noEligible) &&
            new HashSet<>(strings(fc.array("noEpaObservationsGameIds"))).equals(noEpa), "Foundation coverage observation IDs diverge");
    }
    private static void resource(ObjectValue r, Map<String, ObjectValue> resources) {
        fields(r, Set.of("revision_id", "kind", "dependencies", "available_at", "ingested_at", "payload"));
        for (var dep : strings(r.array("dependencies"))) check(resources.containsKey(dep), "Unresolved resource dependency");
        for (var key : List.of("available_at", "ingested_at")) if (!r.isNull(key)) ExactInstant.epochSeconds(r.object(key).text("value"));
        var p = r.object("payload");
        switch (r.text("kind")) {
            case "FILE" -> {
                fields(p, Set.of("source_revision_id", "sha256", "bytes_base64", "origin"));
                check(PythonJson.sha(Base64.getDecoder().decode(p.text("bytes_base64"))).equals(p.text("sha256")) &&
                    r.text("revision_id").equals("sha256:" + p.text("sha256")) && r.text("revision_id").equals(p.text("source_revision_id")), "FILE integrity mismatch");
                check(r.array("dependencies").isEmpty(), "FILE cannot have dependencies");
            }
            case "SET" -> {
                fields(p, Set.of("source_set_id", "source_kind"));
                check(Set.of("calendar", "pbp").contains(p.text("source_kind")) && r.text("revision_id").equals(p.text("source_set_id")), "SET identity mismatch");
                var deps = new ArrayList<>(strings(r.array("dependencies"))); deps.sort(String::compareTo);
                check(!deps.isEmpty() && PythonJson.identity(new ArrayValue(deps.stream().map(x -> (TemporalValue)new TextValue(x)).toList())).equals(r.text("revision_id")), "Source set semantic identity mismatch");
                for (var dep : deps) check(resources.get(dep).text("kind").equals("FILE"), "SET must contain FILE members");
            }
            case "CALENDAR" -> {
                fields(p, Set.of("season", "phase", "games", "complete", "closed_weeks"));
                for (var g : p.array("games")) game(object(g));
            }
            case "STATE" -> {
                fields(p, Set.of("game_id", "calendar_revision_id", "status", "event_upper_bound", "kickoff"), Set.of("source_cause", "event_lower_bound"));
                check(resources.containsKey(p.text("calendar_revision_id")), "STATE/calendar missing");
                for (var key : List.of("event_upper_bound", "event_lower_bound")) if (p.fields().containsKey(key) && !p.isNull(key)) ExactInstant.epochSeconds(p.object(key).text("value"));
            }
            case "METADATA" -> fields(p, Set.of("origin", "document"));
            default -> throw new IllegalArgumentException("Unsupported resource kind");
        }
    }
    private static void calculation(ObjectValue c, Map<String, ObjectValue> resources) {
        fields(c, Set.of("revision_id", "calculation_id", "coverage_revision_id", "calendar_revision_id", "pbp_revision_id",
            "metadata_revision_ids", "game", "versions", "completeness", "model", "source_models", "unknown_filter_flags_n", "statistics"), Set.of("source_cause"));
        text(c.text("calculation_id")); text(c.text("coverage_revision_id")); game(c.object("game"));
        var cal = resources.get(c.text("calendar_revision_id")); var pbp = resources.get(c.text("pbp_revision_id"));
        check(cal != null && cal.text("kind").equals("CALENDAR") && cal.object("payload").array("games").contains(c.object("game")), "Calculation/calendar mismatch");
        check(pbp != null && pbp.text("kind").equals("SET") && pbp.object("payload").text("source_kind").equals("pbp"), "Calculation/PBP mismatch");
        check(c.object("source_models").fields().keySet().equals(new HashSet<>(strings(pbp.array("dependencies")))), "Incomplete source model map");
        for (var mid : strings(c.array("metadata_revision_ids"))) check(resources.containsKey(mid) && resources.get(mid).text("kind").equals("METADATA"), "Calculation/metadata mismatch");
        versions(c.object("versions").text("population"), c.object("versions").text("definition"));
        check(c.object("versions").text("adapter").equals("1.0.0"), "Adapter version mismatch");
        nonnegative(c.integer("unknown_filter_flags_n"));
        var groups = new HashMap<String, ObjectValue>();
        for (var value : c.array("statistics")) {
            var row = object(value);
            fields(row, Set.of("team", "role", "foundation", "eligible_n", "epa_n", "success_n", "epa_missing_n", "epa_nonfinite_n", "epa_sum"));
            sums(row, false); group(row.text("role"), row.text("foundation"));
            check(Set.of(c.object("game").text("home_team"), c.object("game").text("away_team")).contains(row.text("team")), "Statistics participant mismatch");
            check(groups.put(row.text("team") + "/" + row.text("role") + "/" + row.text("foundation"), row) == null, "Duplicate sufficient group");
        }
        check(groups.size() == 12, "Exactly twelve groups per observed game required");
        for (var row : groups.values()) {
            String team = row.text("team"), opponent = c.object("game").text(team.equals(c.object("game").text("home_team")) ? "away_team" : "home_team");
            var other = groups.get(opponent + "/" + (row.text("role").equals("off") ? "def" : "off") + "/" + row.text("foundation"));
            for (var count : COUNTS) check(row.get(count).equals(other.get(count)), "Off/opponent defense count mismatch");
            check(equalDecimal(row.get("epa_sum"), other.get("epa_sum")), "Off/opponent defense EPA mismatch");
            if (row.text("foundation").equals("general")) reconcile(row, groups.get(team + "/" + row.text("role") + "/classified_pass"), groups.get(team + "/" + row.text("role") + "/classified_rush"));
        }
    }
    private static void receipt(ObjectValue r, ObjectValue e) {
        fields(r, Set.of("receiptVersion", "receipt_id", "archive_id", "archive_root", "sha256", "locator", "observed_at", "origin"));
        check(r.integer("receiptVersion").equals(BigInteger.ONE) && PythonJson.identity(r.without("receipt_id")).equals(r.text("receipt_id")), "Receipt identity mismatch");
        check(e.text("subject_id").equals("sha256:" + r.text("sha256")) && r.text("locator").equals("blobs/sha256/" + r.text("sha256").substring(0, 2) + "/" + r.text("sha256")), "Receipt source/locator binding mismatch");
        check(ExactInstant.epochSeconds(e.text("recorded_at")).compareTo(ExactInstant.epochSeconds(r.text("observed_at"))) == 0, "Receipt time mismatch");
    }
    private static void requestedPeriod(ObjectValue b, ObjectValue request) {
        var p = b.object("requestedPeriod");
        fields(p, Set.of("window", "season", "phase", "origin", "mode", "cutoff", "selection"));
        for (var key : List.of("window", "season", "phase", "origin")) check(p.get(key).equals(b.get(key)), "Requested period block mismatch");
        check(p.get("mode").equals(request.get("mode")) && p.get("cutoff").equals(request.get("asOfInstant")), "Requested period cutoff/mode mismatch");
        switch (b.text("window")) {
            case "WEEK_OBSERVATION" -> { fields(p.object("selection"), Set.of("week")); check(p.object("selection").get("week").equals(request.get("week")), "Requested week mismatch"); }
            case "LAST_3_CALENDAR_WEEKS" -> {
                fields(p.object("selection"), Set.of("weeks"));
                int target = request.integer("targetWeek").intValueExact(); var weeks = new ArrayList<TemporalValue>();
                for (int week = Math.max(1, target - 3); week < target; week++) weeks.add(new IntegerValue(BigInteger.valueOf(week)));
                check(p.object("selection").array("weeks").equals(weeks), "Requested weeks signature mismatch");
            }
            case "SEASON_TO_CUTOFF", "HISTORICAL_REFERENCE" -> { fields(p.object("selection"), Set.of("eventEndBefore")); check(p.object("selection").get("eventEndBefore").equals(request.get("asOfInstant")), "Requested event period mismatch"); }
            default -> throw new IllegalArgumentException("Unsupported window");
        }
    }
    private static TemporalResult.Sums sums(ObjectValue s) { return sums(s, true); }
    private static TemporalResult.Sums sums(ObjectValue s, boolean closed) {
        if (closed) fields(s, Set.of("eligible_n", "epa_n", "success_n", "epa_missing_n", "epa_nonfinite_n", "epa_sum"));
        for (var count : COUNTS) nonnegative(s.integer(count));
        check(s.integer("eligible_n").equals(s.integer("epa_n").add(s.integer("epa_missing_n")).add(s.integer("epa_nonfinite_n"))) &&
            s.integer("success_n").compareTo(s.integer("epa_n")) <= 0, "Invalid sufficient-stat counts");
        check(s.isNull("epa_sum") == s.integer("epa_n").equals(BigInteger.ZERO), "EPA null/count mismatch");
        var sum = s.isNull("epa_sum") ? null : decimal(s.text("epa_sum"));
        return new TemporalResult.Sums(s.integer("eligible_n"), s.integer("epa_n"), s.integer("success_n"), s.integer("epa_missing_n"), s.integer("epa_nonfinite_n"), sum);
    }
    private static void reconcile(ObjectValue general, ObjectValue pass, ObjectValue rush) {
        check(pass != null && rush != null, "Missing classified group");
        for (var count : COUNTS) check(general.integer(count).equals(pass.integer(count).add(rush.integer(count))), "General count reconciliation failed");
        if (!general.isNull("epa_sum")) check(decimal(general.text("epa_sum")).compareTo((pass.isNull("epa_sum") ? BigDecimal.ZERO : decimal(pass.text("epa_sum"))).add(rush.isNull("epa_sum") ? BigDecimal.ZERO : decimal(rush.text("epa_sum")))) == 0, "General EPA reconciliation failed");
    }
    private static boolean equalDecimal(TemporalValue a, TemporalValue b) {
        if (a == NullValue.INSTANCE || b == NullValue.INSTANCE) return a == b;
        return decimal(((TextValue)a).value()).compareTo(decimal(((TextValue)b).value())) == 0;
    }
    private static TemporalResult.Ratio ratio(TemporalValue v, BigDecimal numerator, BigInteger denominator) {
        check(v instanceof ObjectValue, "Ratio object required, including zero denominator");
        var r = object(v); fields(r, Set.of("numerator", "denominator", "exact"));
        check(r.integer("denominator").equals(denominator), "Ratio denominator mismatch"); nonnegative(denominator);
        BigDecimal n = r.isNull("numerator") ? null : r.get("numerator") instanceof IntegerValue i ? new BigDecimal(i.value()) : decimal(r.text("numerator"));
        check(numerator == null ? n == null : n != null && numerator.compareTo(n) == 0, "Ratio numerator mismatch");
        if (denominator.signum() == 0) { check(r.isNull("exact"), "Zero denominator ratio must be null"); return new TemporalResult.Ratio(n, denominator, null); }
        check(n != null, "Positive denominator requires numerator");
        BigInteger unscaled = n.unscaledValue(), scale = BigInteger.TEN.pow(Math.max(0, n.scale()));
        if (n.scale() < 0) unscaled = unscaled.multiply(BigInteger.TEN.pow(-n.scale()));
        BigInteger den = denominator.multiply(scale), gcd = unscaled.gcd(den);
        unscaled = unscaled.divide(gcd); den = den.divide(gcd);
        String exact = unscaled.toString() + (den.equals(BigInteger.ONE) ? "" : "/" + den);
        check(r.text("exact").equals(exact), "Exact rational mismatch");
        return new TemporalResult.Ratio(n, denominator, exact);
    }
    private static BigDecimal decimal(String s) { check(s.matches("[+-]?(?:[0-9]+(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?"), "Finite decimal string required"); return new BigDecimal(s); }
    private static void game(ObjectValue g) {
        fields(g, Set.of("game_id", "season", "phase", "round", "week", "home_team", "away_team"));
        text(g.text("game_id")); text(g.text("home_team")); text(g.text("away_team"));
        check(!g.text("home_team").equals(g.text("away_team")) && g.integer("season").compareTo(BigInteger.valueOf(1999)) >= 0 && g.integer("week").signum() > 0, "Invalid frozen game");
        check(g.text("phase").equals("REG") ? !g.isNull("round") && g.text("round").equals("REG") : g.text("phase").equals("POST") && (g.isNull("round") || Set.of("WC", "DIV", "CON", "SB").contains(g.text("round"))), "Invalid explicit phase/round");
    }
    private static void group(String role, String foundation) { check(Set.of("off", "def").contains(role) && Set.of("general", "classified_pass", "classified_rush").contains(foundation), "Invalid role/foundation"); }
    private static void versions(String population, String definition) { check(population.equals("classified-scrimmage-v1") && definition.equals("1.0.0"), "Unsupported metric versions"); }
    private static void id(String value) { check(value.matches("sha256:[0-9a-f]{64}"), "Invalid hash identity"); }
    private static void text(String value) { check(!value.isBlank(), "Nonempty string required"); }
    private static void nonnegative(BigInteger n) { check(n.signum() >= 0, "Nonnegative count required"); }
    private static List<String> strings(List<TemporalValue> values) { return values.stream().map(v -> ((TextValue)v).value()).toList(); }
    private static ObjectValue object(TemporalValue value) { check(value instanceof ObjectValue, "JSON object required"); return (ObjectValue)value; }
    private static Map<String, ObjectValue> index(List<TemporalValue> values, String field) { return index(values, field, false); }
    private static Map<String, ObjectValue> index(List<TemporalValue> values, String field, boolean nested) {
        var result = new HashMap<String, ObjectValue>();
        for (var value : values) { var o = object(value); String id = nested ? o.object(field).text("game_id") : o.text(field); check(result.put(id, o) == null, "Duplicate identity"); }
        return result;
    }
    private static void fields(ObjectValue o, Set<String> required) { fields(o, required, Set.of()); }
    private static void fields(ObjectValue o, Set<String> required, Set<String> optional) {
        var allowed = new HashSet<>(required); allowed.addAll(optional);
        check(o.fields().keySet().containsAll(required) && allowed.containsAll(o.fields().keySet()), "Invalid closed fields: " + required);
    }
    private static void check(boolean condition, String reason) { if (!condition) throw new IllegalArgumentException(reason); }
}
