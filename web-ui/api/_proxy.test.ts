import { describe, expect, it, vi } from "vitest";
import { createProxyHandler } from "./_proxy";

const BASE_URL = "https://core.example.test";
const TOKEN = "server-side-test-token-with-at-least-32-characters";

function request(path: string, init?: RequestInit): Request {
  return new Request(`https://frontend.example.test${path}`, init);
}

describe("Vercel API proxy", () => {
  it("rejects unsupported methods", async () => {
    const response = await createProxyHandler({
      baseUrl: BASE_URL,
      sharedToken: TOKEN,
    })(request("/api/v1/games", { method: "PUT" }));

    expect(response.status).toBe(405);
  });

  it("rejects paths outside the allowlist", async () => {
    const response = await createProxyHandler({
      baseUrl: BASE_URL,
      sharedToken: TOKEN,
    })(request("/api/v1/admin"));

    expect(response.status).toBe(404);
  });

  it("fails safely when server-side configuration is absent", async () => {
    const response = await createProxyHandler({ baseUrl: "", sharedToken: "" })(
      request("/api/v1/health")
    );
    const body = await response.text();

    expect(response.status).toBe(503);
    expect(body).not.toContain("CORE_API_BASE_URL");
    expect(body).not.toContain("CORE_API_SHARED_TOKEN");
  });

  for (const [label, options, forbidden] of [
    ["an HTTP backend URL", { baseUrl: "http://core.example.test", sharedToken: TOKEN }, "http://core.example.test"],
    ["an HTTP localhost backend URL", { baseUrl: "http://localhost:8080", sharedToken: TOKEN }, "http://localhost:8080"],
    ["a backend URL with a path", { baseUrl: `${BASE_URL}/api/v1`, sharedToken: TOKEN }, `${BASE_URL}/api/v1`],
    ["a backend URL with credentials", { baseUrl: "https://user:password@core.example.test", sharedToken: TOKEN }, "user:password"],
    ["a short shared token", { baseUrl: BASE_URL, sharedToken: "too-short" }, "too-short"],
  ] as const) {
    it(`fails safely for ${label}`, async () => {
      const fetchImpl = vi.fn();
      const response = await createProxyHandler({ ...options, fetchImpl })(
        request("/api/v1/health")
      );
      const body = await response.text();

      expect(response.status).toBe(503);
      expect(fetchImpl).not.toHaveBeenCalled();
      expect(body).not.toContain(forbidden);
      expect(body).not.toContain("CORE_API_BASE_URL");
      expect(body).not.toContain("CORE_API_SHARED_TOKEN");
    });
  }

  it("adds the shared token only on the server-side upstream request", async () => {
    const fetchImpl = vi.fn(async (upstream: URL | RequestInfo, init?: RequestInit) => {
      expect(upstream.toString()).toBe(`${BASE_URL}/api/v1/games?season=2026`);
      expect(new Headers(init?.headers).get("X-NFL-Sideline-Token")).toBe(TOKEN);
      expect(new Headers(init?.headers).has("authorization")).toBe(false);
      expect(new Headers(init?.headers).has("cookie")).toBe(false);
      return Response.json([{ gameId: "2026_01_TEST" }], { status: 200 });
    });

    const response = await createProxyHandler({
      baseUrl: BASE_URL,
      sharedToken: TOKEN,
      fetchImpl: fetchImpl as typeof fetch,
    })(
      request("/api/v1/games?season=2026", {
        headers: { authorization: "Bearer browser-token", cookie: "session=browser" },
      })
    );

    expect(response.status).toBe(200);
    expect(fetchImpl).toHaveBeenCalledOnce();
    expect(await response.json()).toEqual([{ gameId: "2026_01_TEST" }]);
  });

  it("preserves an upstream HTTP error status but sanitizes its body", async () => {
    const fetchImpl = vi.fn(async () =>
      Response.json(
        { detail: `database failure at ${BASE_URL} token=${TOKEN}` },
        { status: 503 }
      )
    );

    const response = await createProxyHandler({
      baseUrl: BASE_URL,
      sharedToken: TOKEN,
      fetchImpl: fetchImpl as typeof fetch,
    })(request("/api/v1/games?season=2026"));
    const body = await response.text();

    expect(response.status).toBe(503);
    expect(body).not.toContain(BASE_URL);
    expect(body).not.toContain(TOKEN);
    expect(body).not.toContain("database failure");
  });

  it("preserves an empty upstream 404 as a sanitized JSON response", async () => {
    const fetchImpl = vi.fn(async () => new Response(null, { status: 404 }));

    const response = await createProxyHandler({
      baseUrl: BASE_URL,
      sharedToken: TOKEN,
      fetchImpl: fetchImpl as typeof fetch,
    })(request("/api/v1/games/unknown"));

    expect(response.status).toBe(404);
    expect(response.headers.get("content-type")).toContain("application/json");
    expect(await response.json()).toEqual({
      error: {
        code: "UPSTREAM_ERROR",
        message: "Service temporarily unavailable.",
      },
    });
  });

  it("sanitizes timeouts", async () => {
    const fetchImpl = vi.fn(
      (_upstream: URL | RequestInfo, init?: RequestInit) =>
        new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () =>
            reject(new Error(`timeout for ${BASE_URL} with ${TOKEN}`))
          );
        })
    );

    const response = await createProxyHandler({
      baseUrl: BASE_URL,
      sharedToken: TOKEN,
      fetchImpl: fetchImpl as typeof fetch,
      timeoutMs: 5,
    })(request("/api/v1/health"));
    const body = await response.text();

    expect(response.status).toBe(504);
    expect(body).not.toContain(BASE_URL);
    expect(body).not.toContain(TOKEN);
  });

  it("sanitizes backend failures and never reflects secrets", async () => {
    const fetchImpl = vi.fn(async () => {
      throw new Error(`connection failed: ${BASE_URL} token=${TOKEN}`);
    });

    const response = await createProxyHandler({
      baseUrl: BASE_URL,
      sharedToken: TOKEN,
      fetchImpl: fetchImpl as typeof fetch,
    })(request("/api/v1/health"));
    const body = await response.text();

    expect(response.status).toBe(502);
    expect(body).not.toContain(BASE_URL);
    expect(body).not.toContain(TOKEN);
  });
});
