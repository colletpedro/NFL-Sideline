package com.nflsideline.coreapi.metrics.temporal;

import com.fasterxml.jackson.core.JsonFactory;
import com.fasterxml.jackson.core.StreamReadFeature;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HexFormat;
import static com.nflsideline.coreapi.metrics.temporal.TemporalValue.*;

/** Parity with offline_metrics.artifact.json_bytes (sort_keys, indent=2, UTF-8, newline). */
public final class PythonJson {
    private static final ObjectMapper MAPPER = new ObjectMapper(JsonFactory.builder()
        .enable(StreamReadFeature.STRICT_DUPLICATE_DETECTION).build());
    private PythonJson() {}
    public static TemporalValue parse(byte[] bytes) throws IOException {
        var parser = MAPPER.getFactory().createParser(bytes);
        try (parser) {
            JsonNode root = MAPPER.readTree(parser);
            if (root == null || parser.nextToken() != null) throw new IllegalArgumentException("One JSON document required");
            return value(root);
        }
    }
    private static TemporalValue value(JsonNode node) {
        if (node.isObject()) {
            var fields = new HashMap<String, TemporalValue>();
            node.fields().forEachRemaining(e -> fields.put(e.getKey(), value(e.getValue())));
            return new ObjectValue(fields);
        }
        if (node.isArray()) {
            var values = new ArrayList<TemporalValue>();
            node.forEach(n -> values.add(value(n)));
            return new ArrayValue(values);
        }
        if (node.isTextual()) return new TextValue(node.textValue());
        if (node.isIntegralNumber()) return new IntegerValue(node.bigIntegerValue());
        if (node.isBoolean()) return new BooleanValue(node.booleanValue());
        if (node.isNull()) return NullValue.INSTANCE;
        throw new IllegalArgumentException("Decimal values require strings; floating JSON numbers forbidden");
    }
    public static byte[] bytes(TemporalValue value) {
        return (render(value, 0) + "\n").getBytes(StandardCharsets.UTF_8);
    }
    public static String sha(byte[] bytes) {
        try { return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(bytes)); }
        catch (NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }
    public static String identity(TemporalValue value) { return "sha256:" + sha(bytes(value)); }
    private static int compareUnicode(String a, String b) {
        var ai = a.codePoints().iterator(); var bi = b.codePoints().iterator();
        while (ai.hasNext() && bi.hasNext()) {
            int c = Integer.compare(ai.nextInt(), bi.nextInt()); if (c != 0) return c;
        }
        return Boolean.compare(ai.hasNext(), bi.hasNext());
    }
    private static String render(TemporalValue value, int depth) {
        String indent = "  ".repeat(depth), next = "  ".repeat(depth + 1);
        return switch (value) {
            case ObjectValue o -> {
                if (o.fields().isEmpty()) yield "{}";
                var keys = new ArrayList<>(o.fields().keySet()); keys.sort(PythonJson::compareUnicode);
                var parts = new ArrayList<String>();
                for (var key : keys) parts.add(next + quote(key) + ": " + render(o.get(key), depth + 1));
                yield "{\n" + String.join(",\n", parts) + "\n" + indent + "}";
            }
            case ArrayValue a -> {
                if (a.values().isEmpty()) yield "[]";
                var parts = new ArrayList<String>();
                for (var child : a.values()) parts.add(next + render(child, depth + 1));
                yield "[\n" + String.join(",\n", parts) + "\n" + indent + "]";
            }
            case TextValue s -> quote(s.value());
            case IntegerValue i -> i.value().toString();
            case BooleanValue b -> b.value() ? "true" : "false";
            case NullValue n -> "null";
        };
    }
    private static String quote(String value) {
        var out = new StringBuilder("\"");
        for (int i = 0; i < value.length(); i++) {
            char c = value.charAt(i);
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                case '\b' -> out.append("\\b");
                case '\t' -> out.append("\\t");
                case '\n' -> out.append("\\n");
                case '\f' -> out.append("\\f");
                case '\r' -> out.append("\\r");
                default -> {
                    if (c < 32) out.append(String.format("\\u%04x", (int)c));
                    else if (Character.isHighSurrogate(c)) {
                        if (i + 1 >= value.length() || !Character.isLowSurrogate(value.charAt(i + 1)))
                            throw new IllegalArgumentException("Unpaired Unicode surrogate");
                        out.append(c).append(value.charAt(++i));
                    } else if (Character.isLowSurrogate(c)) throw new IllegalArgumentException("Unpaired Unicode surrogate");
                    else out.append(c);
                }
            }
        }
        return out.append('"').toString();
    }
}
