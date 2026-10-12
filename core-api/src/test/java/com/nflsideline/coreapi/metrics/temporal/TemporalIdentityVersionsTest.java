package com.nflsideline.coreapi.metrics.temporal;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.math.BigDecimal;
import java.math.BigInteger;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashMap;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static org.junit.jupiter.api.Assertions.*;
import static com.nflsideline.coreapi.metrics.temporal.TemporalValue.*;

class TemporalIdentityVersionsTest {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Path NEW = Path.of("../docs/plans/metrics/identities-e5b34/examples");
    @ParameterizedTest @ValueSource(strings={"pit", "reconstruction"})
    void readsExplicitV3WithOriginalBatchAndCoverage(String name) throws Exception {
        var bytes = Files.readAllBytes(NEW.resolve(name).resolve("result.json"));
        var r = new TemporalResultReader().read(NEW.resolve(name));
        assertEquals(PythonJson.parse(bytes), r.document());
        assertEquals("metrics-temporal-1.1.0", r.document().text("algorithmVersion"));
        assertEquals("metrics-temporal-result-v3", r.document().text("resultVersion"));
        if (name.equals("pit")) { assertTrue(r.blocks().get(0).aggregates().isEmpty()); return; }
        var used = r.document().array("calculationsUsed"); assertEquals(2, used.size());
        var first = (ObjectValue)used.get(0); var second = (ObjectValue)used.get(1);
        assertEquals(first.text("calculation_id"), second.text("calculation_id"));
        assertEquals("sha256:9344d1b8902207a39b5321f939da1bae8aaddbb848b33b1155152ac1a38eeca7", first.text("calculation_id"));
        assertNotEquals(first.text("coverage_revision_id"), second.text("coverage_revision_id"));
        assertEquals(first.object("original").object("manifest"), second.object("original").object("manifest"));
        assertNotEquals(first.text("calendar_revision_id"), first.object("original").object("coverage").text("calendar_revision_id"));
        assertEquals(BigInteger.valueOf(3),r.blocks().get(0).coverage().integer("expectedGames"));
        assertEquals("1/3",r.blocks().get(0).coverage().object("sourceRatio").text("exact"));
        var general=r.blocks().get(0).aggregates().stream().filter(a -> a.document().text("role").equals("off") && a.document().text("foundation").equals("general") && a.document().text("scope").equals("AUDITABLE_SUBSET_UNKNOWN")).findFirst().orElseThrow();
        assertEquals(new BigDecimal("-1"),general.sums().epaSum());assertEquals("-1/3",general.epa().exact());
        assertEquals(BigInteger.valueOf(3),general.sums().eligibleN());
        assertTrue(r.blocks().get(0).aggregates().stream().anyMatch(a -> a.document().text("scope").equals("COMPLETE") && a.sums().epaN().signum()==0 && a.sums().epaSum()==null));
    }
    @Test void legacyKnownAlgorithmRemainsSeparate() throws Exception {
        var root=Path.of("../docs/plans/metrics/e5b-3/correction-1.0.1/examples/reconstruction");
        var r=new TemporalResultReader().read(root);
        assertEquals("metrics-temporal-result-v2",r.document().text("resultVersion"));
        assertEquals("metrics-temporal-1.0.1",r.document().text("algorithmVersion"));
        assertFalse(((ObjectValue)r.document().array("calculationsUsed").get(0)).fields().containsKey("original"));
    }
    @ParameterizedTest @ValueSource(strings={"v2-new-algorithm", "v3-old-algorithm", "v3-unknown", "v4"})
    void refusesCrossedAndUnknownVersionsEvenAfterRehashing(String kind) throws Exception {
        var d=example();
        switch(kind) {
            case "v2-new-algorithm" -> d.put("resultVersion","metrics-temporal-result-v2");
            case "v3-old-algorithm" -> d.put("algorithmVersion","metrics-temporal-1.0.1");
            case "v3-unknown" -> d.put("algorithmVersion","metrics-temporal-999");
            case "v4" -> d.put("resultVersion","metrics-temporal-result-v4");
        }
        rehash(d);assertThrows(IllegalArgumentException.class, () -> validate(d));
    }
    @ParameterizedTest @ValueSource(strings={"batch", "coverage", "game", "sources", "missing-original", "calendar-set", "population", "complete", "model"})
    void refusesOriginalDimensionCorruptionWithFreshSemanticHashes(String kind) throws Exception {
        var d=example();var c=(ObjectNode)d.withArray("calculationsUsed").get(0);
        var o=(ObjectNode)c.get("original");var m=(ObjectNode)o.get("manifest");var a=(ObjectNode)o.get("coverage");
        switch(kind) {
            case "batch" -> m.withArray("limitations").add("contradictory global property");
            case "coverage" -> a.put("raw_n",999);
            case "game" -> a.put("game_id","wrong-game");
            case "sources" -> a.put("pbp_revision_id","wrong-set");
            case "missing-original" -> c.remove("original");
            case "calendar-set" -> a.put("calendar_revision_id",c.get("calendar_revision_id").asText());
            case "population" -> ((ObjectNode)m.get("versions")).put("population","unsupported");
            case "complete" -> ((ObjectNode)c.get("completeness")).put("value","PARTIAL");
            case "model" -> m.with("source_model_versions").removeAll();
        }
        rehash(d);assertThrows(Exception.class, () -> validate(d));
    }
    private ObjectNode example() throws Exception {return (ObjectNode)JSON.readTree(Files.readAllBytes(NEW.resolve("reconstruction/result.json")));}
    private TemporalResult validate(ObjectNode d) throws Exception {return new TemporalResultReader().validate((ObjectValue)PythonJson.parse(JSON.writeValueAsBytes(d)));}
    private void rehash(ObjectNode d) throws Exception {
        var parsed=(ObjectValue)PythonJson.parse(JSON.writeValueAsBytes(d));var fields=new HashMap<String,TemporalValue>();
        for(var key:List.of("resultVersion","algorithmVersion","policy","request","asOfDateMapping","pregame","blocks","resourcesUsed","calculationsUsed","evidenceUsed"))fields.put(key,parsed.get(key));
        d.put("result_id",PythonJson.identity(new ObjectValue(fields)));
        parsed=(ObjectValue)PythonJson.parse(JSON.writeValueAsBytes(d));d.put("audit_id",PythonJson.identity(parsed.without("audit_id")));
    }
}
