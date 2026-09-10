const SHARED_TOKEN_HEADER = "X-NFL-Sideline-Token";
const DEFAULT_TIMEOUT_MS = 8_000;
const MAX_REQUEST_BODY_BYTES = 32 * 1024;
const MAX_RESPONSE_BODY_BYTES = 2 * 1024 * 1024;
const MIN_SHARED_TOKEN_LENGTH = 32;

declare const process: {
  env: Record<string, string | undefined>;
};

type Fetch = typeof fetch;

interface ProxyOptions {
  baseUrl?: string;
  sharedToken?: string;
  fetchImpl?: Fetch;
  timeoutMs?: number;
}

interface AllowedRoute {
  methods: readonly string[];
  pattern: RegExp;
}

const ALLOWED_ROUTES: readonly AllowedRoute[] = [
  { methods: ["GET"], pattern: /^\/api\/v1\/health$/ },
  { methods: ["GET"], pattern: /^\/api\/v1\/teams$/ },
  {
    methods: ["GET"],
    pattern: /^\/api\/v1\/teams\/[A-Za-z0-9_-]+\/metrics$/,
  },
  { methods: ["GET"], pattern: /^\/api\/v1\/games$/ },
  { methods: ["GET"], pattern: /^\/api\/v1\/games\/[A-Za-z0-9_-]+$/ },
  { methods: ["POST"], pattern: /^\/api\/v1\/analysis\/matchup$/ },
];

class BodyTooLargeError extends Error {}
class InvalidConfigurationError extends Error {}

function jsonResponse(status: number, code: string, message: string): Response {
  return Response.json(
    { error: { code, message } },
    {
      status,
      headers: {
        "cache-control": "no-store",
        "content-type": "application/json; charset=utf-8",
      },
    }
  );
}

function allowedRoute(pathname: string): AllowedRoute | undefined {
  return ALLOWED_ROUTES.find((route) => route.pattern.test(pathname));
}

function upstreamBaseUrl(rawBaseUrl: string): URL {
  let parsed: URL;
  try {
    parsed = new URL(rawBaseUrl);
  } catch {
    throw new InvalidConfigurationError();
  }

  if (
    parsed.protocol !== "https:" ||
    parsed.username ||
    parsed.password ||
    parsed.search ||
    parsed.hash ||
    (parsed.pathname !== "/" && parsed.pathname !== "")
  ) {
    throw new InvalidConfigurationError();
  }

  return parsed;
}

function validSharedToken(rawToken: string | undefined): string | undefined {
  const token = rawToken?.trim();
  return token && token.length >= MIN_SHARED_TOKEN_LENGTH ? token : undefined;
}

async function requestBody(request: Request): Promise<Uint8Array | undefined> {
  if (request.method !== "POST") return undefined;

  const contentType = request.headers.get("content-type")?.toLowerCase() ?? "";
  if (!contentType.startsWith("application/json")) {
    throw new TypeError("Unsupported content type");
  }

  const declaredLength = Number(request.headers.get("content-length"));
  if (Number.isFinite(declaredLength) && declaredLength > MAX_REQUEST_BODY_BYTES) {
    throw new BodyTooLargeError();
  }

  const body = new Uint8Array(await request.arrayBuffer());
  if (body.byteLength > MAX_REQUEST_BODY_BYTES) {
    throw new BodyTooLargeError();
  }
  return body;
}

function responseBodyWithinLimit(response: Response): Promise<string> {
  const declaredLength = Number(response.headers.get("content-length"));
  if (Number.isFinite(declaredLength) && declaredLength > MAX_RESPONSE_BODY_BYTES) {
    return Promise.reject(new Error("Response body too large"));
  }
  return response.text().then((body) => {
    if (new TextEncoder().encode(body).byteLength > MAX_RESPONSE_BODY_BYTES) {
      throw new Error("Response body too large");
    }
    return body;
  });
}

export function createProxyHandler(options: ProxyOptions = {}) {
  return async function proxy(request: Request): Promise<Response> {
    const requestUrl = new URL(request.url);
    const route = allowedRoute(requestUrl.pathname);
    if (!route) {
      return jsonResponse(404, "NOT_FOUND", "Route not found.");
    }

    if (request.method === "OPTIONS") {
      return new Response(null, {
        status: 204,
        headers: { allow: [...route.methods, "OPTIONS"].join(", ") },
      });
    }

    if (!route.methods.includes(request.method)) {
      return jsonResponse(405, "METHOD_NOT_ALLOWED", "Method not allowed.");
    }

    const baseUrl = options.baseUrl ?? process.env.CORE_API_BASE_URL?.trim();
    const sharedToken = validSharedToken(
      options.sharedToken ?? process.env.CORE_API_SHARED_TOKEN
    );
    if (!baseUrl || !sharedToken) {
      return jsonResponse(
        503,
        "PROXY_UNAVAILABLE",
        "Service temporarily unavailable."
      );
    }

    let upstream: URL;
    let body: Uint8Array | undefined;
    try {
      upstream = new URL(`${requestUrl.pathname}${requestUrl.search}`, upstreamBaseUrl(baseUrl));
      body = await requestBody(request);
    } catch (error) {
      if (error instanceof BodyTooLargeError) {
        return jsonResponse(413, "PAYLOAD_TOO_LARGE", "Request body is too large.");
      }
      if (error instanceof TypeError) {
        return jsonResponse(415, "UNSUPPORTED_MEDIA_TYPE", "Expected a JSON request body.");
      }
      return jsonResponse(
        503,
        "PROXY_UNAVAILABLE",
        "Service temporarily unavailable."
      );
    }

    const controller = new AbortController();
    const timeout = setTimeout(
      () => controller.abort(),
      options.timeoutMs ?? DEFAULT_TIMEOUT_MS
    );

    try {
      const upstreamResponse = await (options.fetchImpl ?? fetch)(upstream, {
        method: request.method,
        headers: {
          accept: "application/json",
          ...(body ? { "content-type": "application/json" } : {}),
          [SHARED_TOKEN_HEADER]: sharedToken,
        },
        body,
        redirect: "manual",
        signal: controller.signal,
      });
      const rawBody = await responseBodyWithinLimit(upstreamResponse);
      if (upstreamResponse.status < 200 || upstreamResponse.status >= 300) {
        const isHttpError =
          upstreamResponse.status >= 400 && upstreamResponse.status <= 599;
        return jsonResponse(
          isHttpError ? upstreamResponse.status : 502,
          "UPSTREAM_ERROR",
          "Service temporarily unavailable."
        );
      }
      const parsedBody: unknown = JSON.parse(rawBody);
      return new Response(JSON.stringify(parsedBody), {
        status: upstreamResponse.status,
        headers: {
          "cache-control": "no-store",
          "content-type": "application/json; charset=utf-8",
        },
      });
    } catch {
      if (controller.signal.aborted) {
        return jsonResponse(504, "UPSTREAM_TIMEOUT", "Service temporarily unavailable.");
      }
      return jsonResponse(502, "UPSTREAM_UNAVAILABLE", "Service temporarily unavailable.");
    } finally {
      clearTimeout(timeout);
    }
  };
}

export const proxyHandler = createProxyHandler();
