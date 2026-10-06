package com.nflsideline.coreapi.editorial.local;

import com.sun.net.httpserver.*;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.mockito.ArgumentCaptor;
import java.io.*;
import java.net.*;
import java.nio.file.*;
import static org.assertj.core.api.Assertions.*;
import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

class LocalServerTest {
    @TempDir Path temp;
    Path contexts() throws Exception {
        Path dir = Files.createDirectory(temp.resolve("contexts"));
        Files.copy(LocalIntegrationTest.fixture(), dir.resolve("game.json"));
        return dir;
    }
    record Exchange(int status, com.fasterxml.jackson.databind.JsonNode body) { }
    Exchange request(HttpHandler handler, String method, String path, String origin) throws Exception {
        var exchange = mock(HttpExchange.class);
        var headers = new Headers();
        headers.set("Host", "127.0.0.1:18081");
        if (origin != null) headers.set("Origin", origin);
        when(exchange.getRequestHeaders()).thenReturn(headers);
        when(exchange.getResponseHeaders()).thenReturn(new Headers());
        when(exchange.getRequestURI()).thenReturn(URI.create(path));
        when(exchange.getRequestMethod()).thenReturn(method);
        var bytes = new ByteArrayOutputStream();
        when(exchange.getResponseBody()).thenReturn(bytes);
        handler.handle(exchange);
        var status = ArgumentCaptor.forClass(Integer.class);
        verify(exchange).sendResponseHeaders(status.capture(), anyLong());
        return new Exchange(status.getValue(), FrozenContext.MAPPER.readTree(bytes.toByteArray()));
    }
    @Test void httpHandlerGeneratesQueriesRejectsPathsAndKeepsErrorsSanitizedWithoutSocket() throws Exception {
        var transport = mock(HttpServer.class);
        when(transport.getAddress()).thenReturn(new InetSocketAddress("127.0.0.1",18081));
        try (var server = new LocalAnalysisServer(contexts(), Files.createDirectory(temp.resolve("results")),18081,transport)) {
            server.start();
            var handler = ArgumentCaptor.forClass(HttpHandler.class);
            verify(transport).createContext(eq(LocalAnalysisServer.PREFIX),handler.capture());
            String route = LocalAnalysisServer.PREFIX + "2026_03_BAL_DAL";
            var generated = request(handler.getValue(),"POST",route,null);
            assertThat(generated.status()).isEqualTo(201);
            assertThat(generated.body().path("analysis").size()).isEqualTo(4);
            var fetched = request(handler.getValue(),"GET",route+"/"+generated.body().path("attemptId").asText(),null);
            assertThat(fetched.status()).isEqualTo(200);
            assertThat(fetched.body()).isEqualTo(generated.body());
            String evidenceDirectory = System.getProperty("local.integration.evidence");
            if (evidenceDirectory != null) {
                Path evidence = Files.createDirectory(Path.of(evidenceDirectory));
                LocalResultStore.write(evidence.resolve("post-response.json"), generated.body());
                LocalResultStore.write(evidence.resolve("get-response.json"), fetched.body());
                LocalResultStore.write(evidence.resolve("transport.json"), java.util.Map.of(
                        "transport", "HttpExchange test double; no socket", "method", "POST",
                        "path", route, "postStatus", generated.status(), "getStatus", fetched.status()));
            }
            assertThat(request(handler.getValue(),"POST",route,"http://evil.test").status()).isEqualTo(400);
            assertThat(request(handler.getValue(),"POST",LocalAnalysisServer.PREFIX+"missing",null).status()).isEqualTo(404);
            for (String suffix : new String[]{"../outside","%2e%2e","%2Ftmp","game?path=/tmp","/tmp/a"}) {
                var error = request(handler.getValue(),"POST",LocalAnalysisServer.PREFIX+suffix,null);
                assertThat(error.status()).isEqualTo(400);
                assertThat(error.body().toString()).doesNotContain(temp.toString(),"Exception");
            }
        }
        verify(transport).stop(0);
    }
    @Test void catalogAndHistoryExposeOnlyMetadataAndVerifiedAttempts() throws Exception {
        var transport = mock(HttpServer.class);
        when(transport.getAddress()).thenReturn(new InetSocketAddress("127.0.0.1",18081));
        Path output = Files.createDirectory(temp.resolve("results"));
        try (var server = new LocalAnalysisServer(contexts(), output,18081,transport)) {
            var handler = ArgumentCaptor.forClass(HttpHandler.class);
            verify(transport).createContext(eq(LocalAnalysisServer.PREFIX),handler.capture());
            var h = handler.getValue();
            String prefix = LocalAnalysisServer.PREFIX, route = prefix + "2026_03_BAL_DAL";
            var catalog = request(h,"GET",prefix,null);
            assertThat(catalog.status()).isEqualTo(200);
            assertThat(catalog.body().size()).isEqualTo(1);
            assertThat(catalog.body().get(0).path("awayTeam").asText()).isEqualTo("BAL");
            assertThat(catalog.body().get(0).path("asOfDate").asText()).isEqualTo("2026-09-22");
            assertThat(catalog.body().toString()).doesNotContain("evidence", "canonicalJson", temp.toString());
            assertThat(request(h,"GET",prefix,"http://evil.test").status()).isEqualTo(400);
            assertThat(request(h,"GET",route+"/attempts",null).body().path("attempts").size()).isZero();
            var generated = request(h,"POST",route,null).body();
            var history = request(h,"GET",route+"/attempts",null);
            assertThat(history.status()).isEqualTo(200);
            assertThat(history.body().path("attempts").size()).isEqualTo(1);
            assertThat(history.body().path("attempts").get(0).path("attemptId")).isEqualTo(generated.path("attemptId"));
            assertThat(history.body().path("unavailableInStore").asInt()).isZero();
            Files.writeString(output.resolve(generated.path("attemptId").asText()).resolve("rendered.json"),"{}");
            Files.createDirectory(output.resolve("unfinished"));
            var corrupted = request(h,"GET",route+"/attempts",null).body();
            assertThat(corrupted.path("attempts").size()).isZero();
            assertThat(corrupted.path("unavailableInStore").asInt()).isEqualTo(2);
            assertThat(request(h,"POST",route+"/attempts",null).status()).isEqualTo(405);
        }
    }
    @Test void startupCannotLoadSpringDatasourceJpaGeminiRepositoriesOrExporter() throws Exception {
        Path input = contexts(), output = Files.createDirectory(temp.resolve("results"));
        var transport = mock(HttpServer.class);
        URL classes = LocalAnalysisServer.class.getProtectionDomain().getCodeSource().getLocation();
        try (var loader = new URLClassLoader(new URL[]{classes}, getClass().getClassLoader()) {
            @Override protected Class<?> loadClass(String name, boolean resolve) throws ClassNotFoundException {
                if (name.startsWith("org.springframework.") || name.startsWith("com.zaxxer.")
                        || name.startsWith("org.hibernate.") || name.startsWith("jakarta.persistence.")
                        || name.startsWith("com.nflsideline.coreapi.repository.")
                        || name.startsWith("com.nflsideline.coreapi.snapshot.")
                        || name.equals("com.nflsideline.coreapi.llm.GeminiClient"))
                    throw new AssertionError("Forbidden initialization dependency: "+name);
                if (name.startsWith("com.nflsideline.")) {
                    var loaded = findLoadedClass(name);
                    if (loaded == null) loaded = findClass(name);
                    if (resolve) resolveClass(loaded);
                    return loaded;
                }
                return super.loadClass(name,resolve);
            }
        }) {
            Class<?> type = loader.loadClass(LocalAnalysisServer.class.getName());
            var constructor = type.getDeclaredConstructor(Path.class,Path.class,int.class,HttpServer.class);
            constructor.setAccessible(true);
            try (var server = (AutoCloseable) constructor.newInstance(input,output,18081,transport)) {
                type.getMethod("start").invoke(server);
                verify(transport).start();
            }
        }
    }
    @Test void normalControllersDoNotExposeLocalEndpointsAndLocalClassesAreNotComponents() throws Exception {
        var service = mock(com.nflsideline.coreapi.service.AnalysisService.class);
        var mvc = org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup(
                new com.nflsideline.coreapi.controller.AnalysisController(service)).build();
        mvc.perform(post("/api/v1/local-analysis/2026_03_BAL_DAL")).andExpect(status().isNotFound());
        mvc.perform(get("/api/v1/local-analysis/2026_03_BAL_DAL/anything")).andExpect(status().isNotFound());
        var scanner = new org.springframework.context.annotation.ClassPathScanningCandidateComponentProvider(true);
        assertThat(scanner.findCandidateComponents("com.nflsideline.coreapi.editorial.local")).isEmpty();
        verifyNoInteractions(service);
    }
}
