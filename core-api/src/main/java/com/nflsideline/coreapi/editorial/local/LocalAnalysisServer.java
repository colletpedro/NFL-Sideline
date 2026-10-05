package com.nflsideline.coreapi.editorial.local;

import com.sun.net.httpserver.*;
import java.io.IOException;
import java.net.*;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.*;

/** Explicit standalone entry. Deliberately not a Spring configuration, bean or controller. */
public final class LocalAnalysisServer implements AutoCloseable {
    public static final String PREFIX = "/api/v1/local-analysis/";
    private final HttpServer server;
    private final ExecutorService executor;
    private final LocalResultStore store;
    private final LocalContextCatalog catalog;
    public LocalAnalysisServer(Path contexts, Path results, int port) throws IOException {
        this(contexts, results, port, null);
    }
    LocalAnalysisServer(Path contexts, Path results, int port, HttpServer transport) throws IOException {
        if (port < 0 || port > 65535) throw new IllegalArgumentException("INVALID_PORT");
        Path input = contexts.toRealPath(), output = results.toRealPath();
        if (input.startsWith(output) || output.startsWith(input)) throw new IllegalArgumentException("OVERLAPPING_DIRECTORIES");
        catalog = new LocalContextCatalog(input);
        store = new LocalResultStore(output);
        HttpServer created = null;
        try {
            created = transport == null ? HttpServer.create(new InetSocketAddress(InetAddress.getByName("127.0.0.1"), port), 32) : transport;
            server = created;
            executor = new ThreadPoolExecutor(2, 4, 30, TimeUnit.SECONDS, new ArrayBlockingQueue<>(32),
                    new ThreadPoolExecutor.CallerRunsPolicy());
            server.setExecutor(executor);
            server.createContext(PREFIX, this::handle);
        } catch (IOException | RuntimeException e) {
            if (created != null) created.stop(0);
            store.close(); throw e;
        }
    }
    public void start() { server.start(); }
    public int port() { return server.getAddress().getPort(); }
    private void handle(HttpExchange exchange) throws IOException {
        try (exchange) {
            int status;
            Object body;
            try {
                String host = exchange.getRequestHeaders().getFirst("Host");
                if (!("127.0.0.1:" + port()).equals(host) || exchange.getRequestHeaders().containsKey("Origin"))
                    throw new IllegalArgumentException("INVALID_LOCAL_REQUEST");
                if (exchange.getRequestURI().getRawQuery() != null || exchange.getRequestURI().getRawPath().contains("%")
                        || exchange.getRequestHeaders().containsKey("Transfer-Encoding")
                        || !Set.of("0", "").contains(Optional.ofNullable(exchange.getRequestHeaders().getFirst("Content-Length")).orElse(""))) throw new IllegalArgumentException("INVALID_LOCAL_REQUEST");
                String[] parts = exchange.getRequestURI().getRawPath().substring(PREFIX.length()).split("/", -1);
                if (parts.length < 1 || parts.length > 2) throw new IllegalArgumentException("INVALID_LOCAL_REQUEST");
                var entry = catalog.get(parts[0]);
                if ("POST".equals(exchange.getRequestMethod()) && parts.length == 1) {
                    body = store.generate(parts[0], entry, new LocalRuleSelector()); status = 201;
                    var result = (LocalResultStore.Response) body;
                    exchange.getResponseHeaders().set("Location", PREFIX + parts[0] + "/" + result.attemptId());
                } else if ("GET".equals(exchange.getRequestMethod()) && parts.length == 2) {
                    body = store.get(parts[0], parts[1]); status = 200;
                } else { body = Map.of("error", "METHOD_OR_ROUTE_NOT_ALLOWED"); status = 405; }
            } catch (IllegalArgumentException e) { status = 400; body = Map.of("error", "INVALID_LOCAL_REQUEST"); }
            catch (NoSuchElementException e) { status = 404; body = Map.of("error", "LOCAL_RESOURCE_NOT_FOUND"); }
            catch (IOException e) { status = 409; body = Map.of("error", "LOCAL_RESULT_UNAVAILABLE"); }
            catch (RuntimeException e) { status = 500; body = Map.of("error", "LOCAL_OPERATION_FAILED"); }
            byte[] bytes = FrozenContext.MAPPER.writeValueAsBytes(body);
            exchange.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
            exchange.getResponseHeaders().set("Cache-Control", "no-store");
            exchange.sendResponseHeaders(status, bytes.length);
            exchange.getResponseBody().write(bytes);
        }
    }
    @Override public void close() throws IOException {
        server.stop(0);
        executor.shutdown();
        try {
            if (!executor.awaitTermination(30, TimeUnit.SECONDS)) executor.shutdownNow();
        } catch (InterruptedException e) { executor.shutdownNow(); Thread.currentThread().interrupt(); }
        store.close();
    }
    public static int run(String[] args) {
        try {
            if (args.length != 3) throw new IllegalArgumentException("Expected contexts results port");
            var server = new LocalAnalysisServer(Path.of(args[0]), Path.of(args[1]), Integer.parseInt(args[2]));
            Runtime.getRuntime().addShutdownHook(new Thread(() -> {
                try { server.close(); } catch (IOException ignored) { }
            }));
            server.start();
            System.out.println("LOCAL_ANALYSIS_READY http://127.0.0.1:" + server.port());
            return 0;
        } catch (Exception e) {
            System.err.println("LOCAL_ANALYSIS_START_FAILED " + e.getClass().getSimpleName());
            return 1;
        }
    }
}
