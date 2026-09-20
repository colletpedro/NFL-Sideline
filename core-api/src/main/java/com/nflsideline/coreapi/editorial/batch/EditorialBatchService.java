package com.nflsideline.coreapi.editorial.batch;

import com.nflsideline.coreapi.llm.GenerationFailure;
import com.nflsideline.coreapi.editorial.AnalysisContext;
import com.nflsideline.coreapi.editorial.AnalysisContextBuilder;
import com.nflsideline.coreapi.editorial.AnalysisDepth;
import com.nflsideline.coreapi.editorial.EditorialCandidate;
import com.nflsideline.coreapi.editorial.EditorialPlanner;
import com.nflsideline.coreapi.editorial.EditorialRoundResolver;
import com.nflsideline.coreapi.editorial.Eligibility;
import com.nflsideline.coreapi.repository.AnalysisCacheRepository;
import com.nflsideline.coreapi.repository.GameRepository;
import com.nflsideline.coreapi.service.AnalysisService;
import org.springframework.context.annotation.Profile;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.EnumMap;
import java.util.List;
import java.util.Map;

@Service
@Profile("editorial")
public class EditorialBatchService {
    private final GameRepository games;
    private final AnalysisCacheRepository caches;
    private final AnalysisContextBuilder contexts;
    private final AnalysisService analyses;
    private final EditorialPlanner planner = new EditorialPlanner(new EditorialRoundResolver());

    public EditorialBatchService(GameRepository games, AnalysisCacheRepository caches,
                                 AnalysisContextBuilder contexts, AnalysisService analyses) {
        this.games = games;
        this.caches = caches;
        this.contexts = contexts;
        this.analyses = analyses;
    }

    public Summary run(EditorialBatchOptions options) {
        List<EditorialCandidate> candidates = planner.plan(
                games.findAllBySeasonWithDetails(options.season()), options.asOfDate());
        List<Planned> planned = candidates.stream().filter(item -> item.eligibility() == Eligibility.ELIGIBLE)
                .map(item -> planned(item, options)).toList();

        Map<AnalysisDepth, Integer> eligible = new EnumMap<>(AnalysisDepth.class);
        planned.forEach(item -> eligible.merge(item.candidate().depth(), 1, Integer::sum));
        int reused = (int) planned.stream().filter(Planned::cached).count();
        List<Planned> calls = planned.stream().filter(item -> !item.cached()).limit(options.maxAnalyses()).toList();
        int omittedByLimit = (int) planned.stream().filter(item -> !item.cached()).count() - calls.size();
        List<String> failures = new ArrayList<>();
        Map<GenerationFailure.Category, Integer> failureCategories = new EnumMap<>(GenerationFailure.Category.class);
        int realized = 0;
        if (!options.dryRun()) {
            for (Planned call : calls) {
                try {
                    analyses.generatePrepared(call.candidate().game(), call.candidate().depth(),
                            options.asOfDate(), options.revisionKey(), call.context());
                    realized++;
                } catch (RuntimeException failure) {
                    var category = GenerationFailure.classify(failure);
                    failureCategories.merge(category, 1, Integer::sum);
                    failures.add(category.name() + ":" + sanitize(call.candidate().game().getGameId()));
                }
            }
        }
        Map<String, Long> omissionReasons = candidates.stream().filter(item -> item.eligibility() == Eligibility.INELIGIBLE)
                .collect(java.util.stream.Collectors.groupingBy(item -> item.reason().name(),
                        java.util.TreeMap::new, java.util.stream.Collectors.counting()));
        return new Summary(Map.copyOf(eligible), reused, calls.size(), realized, omittedByLimit,
                Map.copyOf(omissionReasons), List.copyOf(failures), Map.copyOf(failureCategories), options.dryRun());
    }

    private Planned planned(EditorialCandidate candidate, EditorialBatchOptions options) {
        AnalysisContext context = contexts.build(candidate.game(), options.asOfDate());
        String hash = analyses.promptHash(candidate.depth(), context.canonicalJson(),
                options.asOfDate(), options.revisionKey());
        boolean cached = caches.findByGameIdAndAnalysisTypeAndPromptHash(candidate.game().getGameId(),
                candidate.depth().analysisType(), hash).isPresent();
        return new Planned(candidate, context, hash, cached);
    }

    private String sanitize(String value) { return value.replaceAll("[^A-Za-z0-9_-]", "_"); }

    private record Planned(EditorialCandidate candidate, AnalysisContext context, String promptHash, boolean cached) { }
    public record Summary(Map<AnalysisDepth, Integer> eligible, int cachesReused, int callsPlanned,
                          int callsRealized, int omittedByLimit, Map<String, Long> omissionReasons,
                          List<String> failures, Map<GenerationFailure.Category, Integer> failureCategories, boolean dryRun) { }
}
