package com.nflsideline.coreapi.editorial;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nflsideline.coreapi.domain.AnalysisCache;
import com.nflsideline.coreapi.domain.Game;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Component;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.LocalDate;
import java.time.OffsetDateTime;
import java.time.ZoneOffset;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HexFormat;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

@Component
@Profile("snapshot")
public class ApprovedAnalysisSelector {
    private final EditorialPlanner planner = new EditorialPlanner(new EditorialRoundResolver());
    private final ObjectMapper mapper = new ObjectMapper();

    public SelectionResult select(List<Game> games, LocalDate publicationAsOf,
                                  List<EditorialManifest.Selection> approvals,
                                  List<AnalysisCache> caches) {
        return select(games, publicationAsOf, approvals, caches, Map.of());
    }

    public SelectionResult select(List<Game> games, LocalDate publicationAsOf,
                                  List<EditorialManifest.Selection> approvals,
                                  List<AnalysisCache> caches,
                                  Map<String, PublishedAnalysis> previouslyPublished) {
        Map<String, EditorialCandidate> publicationCandidates = candidates(games, publicationAsOf);
        Map<Long, AnalysisCache> byId = caches.stream()
                .collect(Collectors.toMap(AnalysisCache::getId, Function.identity()));
        List<SelectedAnalysis> valid = new ArrayList<>();
        List<String> problems = new ArrayList<>();
        approvals.stream().sorted(Comparator.comparing(EditorialManifest.Selection::reviewedAt).reversed())
                .forEach(approval -> {
                    AnalysisCache cache = byId.get(approval.analysisCacheId());
                    EditorialCandidate publication = publicationCandidates.get(approval.gameId());
                    boolean accepted = cache != null && publication != null && compatibleHashes(approval, cache)
                            && (approval.depth() == AnalysisDepth.LEGACY_PUBLISHED
                            ? validLegacy(cache, publication.game(), publicationAsOf,
                                    previouslyPublished.get(approval.gameId()))
                            : validNewApproval(approval, cache, publication, games, publicationAsOf));
                    if (!accepted) {
                        problems.add("approval_incompatible");
                    } else if (valid.stream().noneMatch(item -> item.cache().getGameId().equals(approval.gameId()))) {
                        valid.add(new SelectedAnalysis(cache, approval));
                    }
                });
        return new SelectionResult(valid.stream().map(SelectedAnalysis::cache).toList(), List.copyOf(problems));
    }

    private Map<String, EditorialCandidate> candidates(List<Game> games, LocalDate date) {
        return planner.plan(games, date).stream()
                .collect(Collectors.toMap(candidate -> candidate.game().getGameId(), Function.identity()));
    }

    private boolean validNewApproval(EditorialManifest.Selection approval, AnalysisCache cache,
                                     EditorialCandidate publication, List<Game> games,
                                     LocalDate publicationAsOf) {
        if (!approval.depth().analysisType().equals(cache.getAnalysisType())
                || !contextAsOf(cache).equals(approval.asOfDate().toString())) {
            return false;
        }
        EditorialCandidate generation = planner.planForHistoricalEligibility(games, approval.asOfDate()).stream()
                .filter(candidate -> candidate.game().getGameId().equals(approval.gameId()))
                .findFirst().orElse(null);
        if (generation == null || generation.eligibility() != Eligibility.ELIGIBLE
                || generation.depth() != approval.depth()) {
            return false;
        }
        Game game = publication.game();
        if (EditorialPlanner.isFinished(game, publicationAsOf)) {
            LocalDate reviewedDateUtc = approval.reviewedAt().withOffsetSameInstant(ZoneOffset.UTC).toLocalDate();
            return game.getGameday() != null && !reviewedDateUtc.isAfter(game.getGameday());
        }
        return publication.eligibility() == Eligibility.ELIGIBLE
                && publication.depth() == approval.depth();
    }

    private boolean validLegacy(AnalysisCache cache, Game game, LocalDate publicationAsOf,
                                PublishedAnalysis previous) {
        return "matchup".equals(cache.getAnalysisType())
                && EditorialPlanner.isFinished(game, publicationAsOf)
                && previous != null
                && previous.matches(cache, mapper);
    }

    private boolean compatibleHashes(EditorialManifest.Selection approval, AnalysisCache cache) {
        return approval.gameId().equals(cache.getGameId())
                && approval.promptHash().equals(cache.getPromptHash())
                && approval.responseHash().equals(sha256(cache.getResponseText()));
    }

    private String contextAsOf(AnalysisCache cache) {
        try {
            return mapper.readTree(cache.getContextJson()).at("/game/as_of_date_utc").asText("");
        } catch (Exception failure) {
            return "";
        }
    }

    private String sha256(String input) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256")
                    .digest(input.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalStateException("SHA-256 unavailable", e);
        }
    }

    public record PublishedAnalysis(OffsetDateTime createdAt, String fatorChave, String vantagemTatica,
                                    String alertaVermelho, String veredito) {
        boolean matches(AnalysisCache cache, ObjectMapper mapper) {
            try {
                JsonNode response = mapper.readTree(cache.getResponseText());
                return cache.getCreatedAt() != null && createdAt != null
                        && cache.getCreatedAt().toInstant().equals(createdAt.toInstant())
                        && text(response, "fator_chave").equals(fatorChave)
                        && text(response, "vantagem_tatica").equals(vantagemTatica)
                        && text(response, "alerta_vermelho").equals(alertaVermelho)
                        && text(response, "veredito").equals(veredito);
            } catch (Exception failure) {
                return false;
            }
        }

        private String text(JsonNode node, String field) {
            return node.path(field).isTextual() ? node.path(field).textValue() : "";
        }
    }

    private record SelectedAnalysis(AnalysisCache cache, EditorialManifest.Selection approval) { }
    public record SelectionResult(List<AnalysisCache> analyses, List<String> problems) { }
}
