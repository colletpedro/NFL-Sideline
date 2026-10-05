package com.nflsideline.coreapi.editorial.local;

import com.nflsideline.coreapi.editorial.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;
import static org.assertj.core.api.Assertions.*;

class LocalIntegrationTest {
    @TempDir Path temp;
    static Path repo() { return Path.of("..").toAbsolutePath().normalize(); }
    static Path fixture() { return repo().resolve("editorial/evaluations/2026-09-26/contexts/2026_03_BAL_DAL.json"); }
    LocalContextCatalog catalog() throws Exception {
        Path input = Files.createDirectory(temp.resolve("contexts"));
        Files.copy(fixture(), input.resolve("context.json"));
        return new LocalContextCatalog(input);
    }
    @Test void serviceCliPreserveBaselineSemanticsWithOnlyDocumentedRangePresentationChange() throws Exception {
        Path cases = repo().resolve("editorial/coverage-clarity-v1/batch-01");
        int checked = 0;
        try (var dirs = Files.list(cases)) {
            for (Path old : dirs.filter(Files::isDirectory).toList()) {
                if (!Files.exists(old.resolve("context.json"))) continue;
                checked++;
                var context = FrozenContext.read(FrozenContext.MAPPER.readTree(old.resolve("context.json").toFile()));
                var result = new LocalGenerationService().generate(context, FrozenContext.parameters(context), new LocalRuleSelector());
                Path output = temp.resolve(old.getFileName());
                assertThat(LocalAnalysisApplication.run(new String[]{old.resolve("context.json").toString(), output.toString()})).isZero();
                for (String name : List.of("selection.json", "claims.json", "rendered.json")) {
                    var expected = FrozenContext.MAPPER.readTree(old.resolve(name).toFile());
                    if (name.equals("rendered.json") && old.getFileName().toString().equals("2026_03_LV_NO")) {
                        String previous = expected.path("alerta_vermelho").asText();
                        assertThat(previous).contains("faixa semanal de 0 < EPA < 0,0005 a +0,116 EPA");
                        ((com.fasterxml.jackson.databind.node.ObjectNode) expected).put("alerta_vermelho",
                                previous.replace("faixa semanal de 0 < EPA < 0,0005 a +0,116 EPA",
                                        "faixa semanal: mínimo (0 < EPA < 0,0005); máximo (+0,116 EPA)"));
                    }
                    assertThat(FrozenContext.MAPPER.readTree(output.resolve(name).toFile()))
                            .isEqualTo(expected);
                }
                assertThat(FrozenContext.MAPPER.<com.fasterxml.jackson.databind.JsonNode>valueToTree(result.texts()))
                        .isEqualTo(FrozenContext.MAPPER.readTree(output.resolve("rendered.json").toFile()));
                assertThat(FrozenContext.MAPPER.readTree(FrozenContext.MAPPER.writeValueAsBytes(result.selection())))
                        .isEqualTo(FrozenContext.MAPPER.readTree(output.resolve("selection.json").toFile()));
                assertThat(result.selection().document().verdict()).isEqualTo("INCONCLUSIVE");
                assertThat(result.selection().document().thesisTeam()).isEqualTo("NONE");
                assertThat(result.identity().hash()).isEqualTo(FrozenContext.MAPPER.readTree(output.resolve("result.json").toFile()).path("resultIdentity").asText());
            }
        }
        assertThat(checked).isEqualTo(21);
    }
    static ClaimSelector invalidSelector() {
        return new ClaimSelector() {
            public SelectorIdentity identity() { return new SelectorIdentity("invalid-test", "1"); }
            public ClaimSelection select(AnalysisContext context, EditorialParameters p) {
                var good = new LocalRuleSelector().select(context, p);
                var d = good.document();
                return new ClaimSelection(identity(), new ClaimSelection.ClaimDocument(5, "HOME", "HOME_WIN",
                        d.claims(), d.sections(), d.links(), d.groupings()), good.candidates(), good.decisions());
            }
        };
    }
    @Test void commonValidationRejectsInvalidClaimsAndKeepsFailedAttemptUnusable() throws Exception {
        var entry = catalog().get("2026_03_BAL_DAL");
        var selector = invalidSelector();
        var selection = selector.select(entry.context(), FrozenContext.parameters(entry.context()));
        assertThatThrownBy(() -> new ClaimValidator().validate(FrozenContext.MAPPER.valueToTree(selection.document()), entry.context()))
                .isInstanceOf(RuntimeException.class);
        assertThatThrownBy(() -> new LocalGenerationService().generate(entry.context(), FrozenContext.parameters(entry.context()), selector))
                .isInstanceOf(LocalGenerationService.Rejected.class);
        Path output = Files.createDirectory(temp.resolve("results"));
        try (var store = new LocalResultStore(output)) {
            assertThatThrownBy(() -> store.generate("2026_03_BAL_DAL", entry, selector)).hasMessage("LOCAL_GENERATION_FAILED");
            try (var files = Files.list(output)) {
                var failed = files.filter(Files::isDirectory).findFirst().orElseThrow();
                assertThat(failed.resolve("failure.json")).exists();
                assertThat(failed.resolve("complete.json")).doesNotExist();
                assertThatThrownBy(() -> store.get("2026_03_BAL_DAL", failed.getFileName().toString())).hasMessage("INCOMPLETE_RESULT");
            }
        }
    }
    @Test void repeatConcurrentRestartCorruptionAndIncompleteResults() throws Exception {
        var entry = catalog().get("2026_03_BAL_DAL");
        Path output = Files.createDirectory(temp.resolve("results"));
        var responses = new ArrayList<LocalResultStore.Response>();
        try (var store = new LocalResultStore(output); var pool = Executors.newFixedThreadPool(4)) {
            assertThatThrownBy(() -> new LocalResultStore(output)).isInstanceOf(Exception.class);
            var tasks = new ArrayList<Callable<LocalResultStore.Response>>();
            for (int i=0; i<12; i++) tasks.add(() -> store.generate("2026_03_BAL_DAL", entry, new LocalRuleSelector()));
            for (var future : pool.invokeAll(tasks)) responses.add(future.get());
            assertThat(responses.stream().map(LocalResultStore.Response::attemptId).distinct().count()).isEqualTo(12);
            assertThat(responses.stream().map(LocalResultStore.Response::resultIdentity).distinct().count()).isEqualTo(1);
            for (var response : responses) assertThat(store.get(response.gameId(), response.attemptId())).isEqualTo(response);
        }
        try (var store = new LocalResultStore(output)) {
            var response = responses.getFirst();
            assertThat(store.get(response.gameId(), response.attemptId())).isEqualTo(response);
            Files.writeString(output.resolve(response.attemptId()).resolve("rendered.json"), "{}");
            assertThatThrownBy(() -> store.get(response.gameId(), response.attemptId())).hasMessage("INCOMPLETE_RESULT");
            String incomplete = UUID.randomUUID().toString();
            Files.createDirectory(output.resolve(incomplete));
            assertThatThrownBy(() -> store.get(response.gameId(), incomplete)).hasMessage("INCOMPLETE_RESULT");
            assertThatThrownBy(() -> store.get(response.gameId(), "../outside")).isInstanceOf(IllegalArgumentException.class);
        }
    }
    @Test void identitiesSeparateSelectorsVersionsContractsRendererAndParameters() throws Exception {
        var c = catalog().get("2026_03_BAL_DAL").context();
        var p = FrozenContext.parameters(c);
        var s = new LocalRuleSelector().identity();
        var ids = new HashSet<String>();
        ids.add(LocalGenerationService.identity(c,p,s,5,ClaimRenderer.VERSION).hash());
        ids.add(LocalGenerationService.identity(c,p,new ClaimSelector.SelectorIdentity("other",s.version()),5,ClaimRenderer.VERSION).hash());
        ids.add(LocalGenerationService.identity(c,p,new ClaimSelector.SelectorIdentity(s.name(),"future"),5,ClaimRenderer.VERSION).hash());
        ids.add(LocalGenerationService.identity(c,p,s,4,ClaimRenderer.VERSION).hash());
        ids.add(LocalGenerationService.identity(c,p,s,5,"future-renderer").hash());
        ids.add(LocalGenerationService.identity(c,new EditorialParameters(p.season(),p.gameWeek()+1,p.phase()),s,5,ClaimRenderer.VERSION).hash());
        assertThat(ids).hasSize(6);
    }
    @Test void catalogRejectsDuplicateIdsInvalidContextsSymlinksAndTraversalAndFreezesBytes() throws Exception {
        var c = catalog();
        Path input = temp.resolve("contexts");
        assertThatThrownBy(() -> c.get("../context")).isInstanceOf(IllegalArgumentException.class);
        assertThatThrownBy(() -> c.get("missing")).isInstanceOf(NoSuchElementException.class);
        Files.copy(fixture(), input.resolve("duplicate.json"));
        assertThatThrownBy(() -> new LocalContextCatalog(input)).hasMessage("AMBIGUOUS_GAME_ID");
        Files.delete(input.resolve("duplicate.json"));
        Files.createSymbolicLink(input.resolve("escape.json"), fixture());
        assertThatThrownBy(() -> new LocalContextCatalog(input)).hasMessage("INVALID_CATALOG_ENTRY");
        Files.delete(input.resolve("escape.json"));
        Files.writeString(input.resolve("context.json"), "{}");
        assertThatThrownBy(() -> new LocalContextCatalog(input)).isInstanceOf(IllegalArgumentException.class);
        assertThat(c.get("2026_03_BAL_DAL").context().homeTeam()).isNotBlank();
        Path publicDir = Files.createDirectory(temp.resolve("public"));
        Path alias = Files.createSymbolicLink(temp.resolve("alias"), publicDir);
        assertThatThrownBy(() -> new LocalResultStore(alias)).hasMessage("PUBLIC_OUTPUT_FORBIDDEN");
    }
}
