package com.nflsideline.coreapi.metrics.temporal;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Base64;
import java.util.Map;
import java.util.HashMap;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import static org.junit.jupiter.api.Assertions.*;
import static com.nflsideline.coreapi.metrics.temporal.TemporalValue.*;

class TemporalResultReaderTest {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Path EXAMPLES = Path.of("../docs/plans/metrics/e5b-3/correction-1.0.1/examples");
    @TempDir Path tmp;
    @ParameterizedTest @ValueSource(strings={"point-in-time", "reconstruction", "unproven"})
    void acceptsCurrentExamplesPreservingAllData(String example) throws Exception {
        var root = EXAMPLES.resolve(example);
        var before = Files.readAllBytes(root.resolve("result.json"));
        var result = new TemporalResultReader().read(root);
        assertArrayEquals(before, Files.readAllBytes(root.resolve("result.json")));
        assertEquals(PythonJson.parse(before), result.document());
        assertEquals("NOT_ESTIMATED", result.guarantees().text("statisticalUncertainty"));
        assertThrows(UnsupportedOperationException.class, () -> result.document().fields().clear());
        assertThrows(UnsupportedOperationException.class, () -> result.blocks().clear());
        assertThrows(UnsupportedOperationException.class, () -> result.document().array("blocks").clear());
        if (example.equals("reconstruction")) {
            assertEquals("NOT_DEMONSTRATED", result.guarantees().text("knowledgeAtCutoff"));
            assertTrue(result.blocks().stream().flatMap(b -> b.aggregates().stream()).anyMatch(a -> a.document().text("role").equals("def")));
            assertTrue(result.blocks().stream().anyMatch(b -> !b.coverage().array("gaps").isEmpty()));
        }
    }
    @Test void pythonCanonicalParityVectors() throws Exception {
        var vectorPath = Path.of("src/test/resources/metrics-temporal/python-canonical-vectors.json");
        var vectors = (ArrayValue) PythonJson.parse(Files.readAllBytes(vectorPath));
        for (var v : vectors.values()) {
            var vector = (ObjectValue)v;
            assertArrayEquals(Base64.getDecoder().decode(vector.text("bytes_base64")), PythonJson.bytes(vector.get("value")));
            assertEquals(vector.text("identity"), PythonJson.identity(vector.get("value")));
        }
    }
    @Test void exactInstantNeverTruncatesAndNormalizesOffsets() {
        var x = ExactInstant.epochSeconds("2026-10-11T09:00:00.12345678901234567890123456789-03:00");
        assertEquals(0,x.compareTo(ExactInstant.epochSeconds("2026-10-11T12:00:00.12345678901234567890123456789Z")));
        assertTrue(x.compareTo(ExactInstant.epochSeconds("2026-10-11T12:00:00.12345678901234567890123456788Z"))>0);
        assertThrows(IllegalArgumentException.class, () -> ExactInstant.epochSeconds("2026-10-11T12:00:00"));
    }
    @Test void rejectsV1ExplicitlyAndUnsupportedAlgorithm() throws Exception {
        var d = example(); d.put("resultVersion","metrics-temporal-result-v1");
        assertTrue(assertThrows(IllegalArgumentException.class, () -> validate(d)).getMessage().contains("v1 refused"));
        d.put("resultVersion","metrics-temporal-result-v2"); d.put("algorithmVersion","metrics-temporal-999");
        assertThrows(IllegalArgumentException.class, () -> validate(d));
    }
    @Test void rejectsDuplicateFieldsFloatAndTrailingDocuments() {
        assertThrows(Exception.class, () -> PythonJson.parse("{\"a\":1,\"a\":2}".getBytes()));
        assertThrows(Exception.class, () -> PythonJson.parse("{\"a\":0.1}".getBytes()));
        assertThrows(Exception.class, () -> PythonJson.parse("{} {}".getBytes()));
    }
    @ParameterizedTest @ValueSource(strings={"byte", "marker", "symlink", "missing"})
    void rejectsArtifactTransportFailures(String kind) throws Exception {
        Path source=EXAMPLES.resolve("reconstruction"), destination=tmp.resolve(kind);Files.createDirectory(destination);
        for(var name:List.of("COMPLETED.json","result.json")) Files.copy(source.resolve(name),destination.resolve(name));
        if(kind.equals("byte")) Files.writeString(destination.resolve("result.json"),"{}");
        if(kind.equals("marker")) {var marker=(ObjectNode)JSON.readTree(Files.readAllBytes(destination.resolve("COMPLETED.json")));marker.put("result_id","wrong");Files.writeString(destination.resolve("COMPLETED.json"),marker.toString());}
        if(kind.equals("missing")) Files.delete(destination.resolve("result.json"));
        if(kind.equals("symlink")) {Files.delete(destination.resolve("result.json"));Files.createSymbolicLink(destination.resolve("result.json"),source.resolve("result.json").toAbsolutePath());}
        assertThrows(Exception.class, () -> new TemporalResultReader().read(destination));
    }
    @ParameterizedTest @ValueSource(strings={"ratio", "counts", "sum-null", "off-def", "group", "period", "association", "file", "set", "receipt", "guarantee", "extra"})
    void rejectsSemanticInvariantFailuresEvenAfterRehashing(String kind) throws Exception {
        var d=example();
        var b=(ObjectNode)d.withArray("blocks").get(0);
        var a=(ObjectNode)b.withArray("aggregates").get(0);
        var c=(ObjectNode)d.withArray("calculationsUsed").get(0);
        var s=(ObjectNode)c.withArray("statistics").get(0);
        switch(kind) {
            case "ratio" -> ((ObjectNode)a.get("epa")).put("exact","999/17");
            case "counts" -> s.put("eligible_n",999);
            case "sum-null" -> { for(var row:c.withArray("statistics")) if(row.get("epa_n").asInt()>0){((ObjectNode)row).putNull("epa_sum");break;} }
            case "off-def" -> s.put("epa_sum","-123.12345678901234567890123456789");
            case "group" -> c.withArray("statistics").remove(0);
            case "period" -> ((ObjectNode)b.get("requestedPeriod").get("selection")).put("eventEndBefore","2000-01-01T00:00:00Z");
            case "association" -> {for(var ev:b.withArray("events"))if(!ev.get("calculationId").isNull()){((ObjectNode)ev).put("calculationId","wrong");break;}}
            case "file" -> {for(var r:d.withArray("resourcesUsed"))if(r.get("kind").asText().equals("FILE")){((ObjectNode)r.get("payload")).put("bytes_base64","Y29ycnVwdA==");break;}}
            case "set" -> {for(var r:d.withArray("resourcesUsed"))if(r.get("kind").asText().equals("SET")){((ObjectNode)r.get("payload")).put("source_set_id","wrong");break;}}
            case "receipt" -> {for(var e:d.withArray("evidenceUsed"))if(e.has("receipt")){((ObjectNode)e.get("receipt")).put("locator","../wrong");break;}}
            case "guarantee" -> ((ObjectNode)d.get("guarantees")).put("knowledgeAtCutoff","CERTIFIED");
            case "extra" -> d.put("unexpected",true);
        }
        rehash(d);
        assertThrows(Exception.class, () -> validate(d));
    }
    @Test void refusesInvalidSemanticIdsWithValidByteHash() throws Exception {
        var d=example();d.put("result_id","sha256:"+"0".repeat(64));
        assertThrows(IllegalArgumentException.class, () -> validate(d));
    }
    @Test void dispatchRunsOfflineWithoutSpring() {
        assertEquals(0,TemporalReadApplication.run(new String[]{"--artifact",EXAMPLES.resolve("reconstruction").toString()}));
        assertEquals(2,TemporalReadApplication.run(new String[]{}));
    }
    @Test void materializedBridgeGoldenKeepsNegativeExactZeroNullUnknownAndEmptyComplete() throws Exception {
        var root=Path.of("src/test/resources/metrics-temporal/materialized-example");
        var result=new TemporalResultReader().read(root);
        var block=result.blocks().get(0);
        assertEquals(java.math.BigInteger.valueOf(3),block.coverage().integer("expectedGames"));
        assertEquals("1/3",block.coverage().object("sourceRatio").text("exact"));
        assertEquals("SOURCE_UNKNOWN",((ObjectValue)block.coverage().array("gaps").get(0)).text("reason"));
        var aggregate=block.aggregates().stream().filter(a -> a.document().text("role").equals("off") && a.document().text("foundation").equals("general") && a.document().text("scope").equals("AUDITABLE_SUBSET_UNKNOWN")).findFirst().orElseThrow();
        assertEquals(new BigDecimal("-1"),aggregate.sums().epaSum());
        assertEquals("-1/3",aggregate.epa().exact());
        assertEquals("UNKNOWN",aggregate.document().text("model"));
        assertFalse(aggregate.document().bool("comparisonEligible"));
        assertTrue(block.aggregates().stream().anyMatch(a -> a.document().text("scope").equals("COMPLETE") && a.sums().epaSum()==null && a.sums().eligibleN().signum()==0));
        var calculations=result.document().array("calculationsUsed");
        var observed=calculations.stream().map(v -> (ObjectValue)v).filter(c -> c.object("game").text("game_id").equals("synthetic-1")).findFirst().orElseThrow();
        var pass=observed.array("statistics").stream().map(v -> (ObjectValue)v).filter(s -> s.text("team").equals("A") && s.text("role").equals("off") && s.text("foundation").equals("classified_pass")).findFirst().orElseThrow();
        assertEquals(new BigDecimal("-1.123456789012345678901234567890123456789"),pass.decimal("epa_sum"));
        // Observed zero EPA is encoded in the original source bytes and counted in epa_n;
        // a source with no EPA retains a null sum, never BigDecimal.ZERO by default.
        assertEquals(java.math.BigInteger.valueOf(2),pass.integer("epa_n"));
        assertTrue(observed.array("statistics").stream().map(v -> (ObjectValue)v).anyMatch(s -> s.isNull("epa_sum") && s.integer("epa_n").signum()==0));
        assertEquals("NOT_DEMONSTRATED",result.guarantees().text("knowledgeAtCutoff"));
        assertFalse(result.guarantees().array("unknownKnowledgeResourceIds").isEmpty());
    }
    @Test void exactObservedZeroAndIncompatibleModelsStaySeparated() throws Exception {
        var result=new TemporalResultReader().read(Path.of("src/test/resources/metrics-temporal/zero-mixed-models"));
        assertEquals(2,result.blocks().get(0).aggregates().stream().map(a -> a.document().text("model")).distinct().count());
        for(var b:result.blocks()) for(var a:b.aggregates()) {
            if(a.sums().epaN().signum()>0) {
                assertEquals(0,a.sums().epaSum().compareTo(BigDecimal.ZERO));
                assertEquals("0",a.epa().exact());
                assertNotNull(a.sums().epaSum());
            } else {assertNull(a.sums().epaSum());assertNull(a.epa().exact());}
            assertFalse(a.document().bool("comparisonEligible"));
            if (b.aggregates().stream().map(x -> x.document().text("model")).distinct().count()>1)
                assertTrue(a.document().array("comparisonFailures").contains(new TextValue("INCOMPATIBLE_EPA_MODELS_SEPARATED")));
        }
    }
    private ObjectNode example() throws Exception { return (ObjectNode)JSON.readTree(Files.readAllBytes(EXAMPLES.resolve("reconstruction/result.json"))); }
    private TemporalResult validate(ObjectNode d) throws Exception { return new TemporalResultReader().validate((ObjectValue)PythonJson.parse(JSON.writeValueAsBytes(d))); }
    private void rehash(ObjectNode d) throws Exception {
        var parsed=(ObjectValue)PythonJson.parse(JSON.writeValueAsBytes(d));
        var fields=new HashMap<String,TemporalValue>();
        for(var key:List.of("resultVersion","algorithmVersion","policy","request","asOfDateMapping","pregame","blocks","resourcesUsed","calculationsUsed","evidenceUsed"))fields.put(key,parsed.get(key));
        d.put("result_id",PythonJson.identity(new ObjectValue(fields)));
        parsed=(ObjectValue)PythonJson.parse(JSON.writeValueAsBytes(d));
        d.put("audit_id",PythonJson.identity(parsed.without("audit_id")));
    }
}
