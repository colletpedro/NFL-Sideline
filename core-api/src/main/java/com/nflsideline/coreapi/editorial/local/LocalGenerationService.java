package com.nflsideline.coreapi.editorial.local;

import com.fasterxml.jackson.annotation.JsonProperty;
import com.nflsideline.coreapi.editorial.*;
import com.fasterxml.jackson.databind.JsonNode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.HexFormat;

/** Shared selection -> common validation -> rendering. No application/container or provider lifecycle. */
public final class LocalGenerationService {
    public static final String VERSION = "local-generation-1.1.0";
    public record Texts(@JsonProperty("fator_chave") String fatorChave,
                        @JsonProperty("vantagem_tatica") String vantagemTatica,
                        @JsonProperty("alerta_vermelho") String alertaVermelho, String veredito) { }
    public record Identity(String schema, String contextSha256, ClaimSelector.SelectorIdentity selector,
                           int contractVersion, String rendererVersion, EditorialParameters parameters) {
        public String hash() {
            try { return sha256(FrozenContext.MAPPER.writeValueAsBytes(this)); }
            catch (java.io.IOException e) { throw new IllegalStateException(e); }
        }
    }
    public record Result(Texts texts, ClaimSelection selection, Identity identity, JsonNode insights) { }
    public static final class Rejected extends RuntimeException {
        private final ClaimSelection selection;
        Rejected(ClaimSelection selection, RuntimeException cause) { super("LOCAL_CLAIMS_REJECTED", cause); this.selection = selection; }
        public ClaimSelection selection() { return selection; }
    }
    public Result generate(AnalysisContext context, EditorialParameters parameters, ClaimSelector selector) {
        return generate(context, parameters, selector, null);
    }
    public Result generate(AnalysisContext context, EditorialParameters parameters, ClaimSelector selector,
                           String declaredAsOfDate) {
        FrozenContext.check(context, parameters);
        FrozenContext.checkCanonical(context);
        if (!parameters.equals(FrozenContext.parameters(context))) throw new IllegalArgumentException("Calendar mismatch");
        ClaimSelection selection = selector.select(context, parameters);
        try {
            if (!selector.identity().equals(selection.selector())) throw new IllegalArgumentException("Selector mismatch");
            var document = FrozenContext.MAPPER.valueToTree(selection.document());
            var validated = new ClaimValidator().validate(document, context);
            var rendered = new ClaimRenderer(FrozenContext.MAPPER).render(validated);
            var texts = FrozenContext.MAPPER.convertValue(rendered, Texts.class);
            var identity = identity(context, parameters, selector.identity(), selection.document().version(), ClaimRenderer.VERSION);
            JsonNode insights;
            try {
                insights = VisualAnalysisProjector.project(context, parameters, validated, selection.document(), identity,
                        declaredAsOfDate);
                VisualAnalysisProjector.verify(context, parameters, validated, selection.document(), identity,
                        declaredAsOfDate, insights);
            } catch (VisualAnalysisProjector.UnsupportedVisualContract unsupported) {
                insights = null; // Textual v3 remains available until a coordinated contract revision.
            }
            return new Result(texts, selection, identity, insights);
        } catch (RuntimeException failure) { throw new Rejected(selection, failure); }
    }
    public static Identity identity(AnalysisContext context, EditorialParameters parameters,
                                    ClaimSelector.SelectorIdentity selector, int contract, String renderer) {
        return new Identity("local-result-1", sha256(context.canonicalJson().getBytes(StandardCharsets.UTF_8)),
                selector, contract, renderer, parameters);
    }
    public static String sha256(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch (java.security.NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }
}
