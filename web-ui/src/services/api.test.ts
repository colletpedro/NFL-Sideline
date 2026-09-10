import { describe, expect, it } from "vitest";
import { normalizeApiBaseUrl, resolveApiBaseUrl } from "./api";

describe("API base URL", () => {
  it("uses localhost for local development", () => {
    expect(resolveApiBaseUrl("development")).toBe(
      "http://localhost:8080/api/v1"
    );
  });

  it("uses the same-origin API in production", () => {
    expect(resolveApiBaseUrl("production")).toBe("/api/v1");
    expect(
      resolveApiBaseUrl(
        "production",
        "https://direct-backend.example/api/v1"
      )
    ).toBe("/api/v1");
  });

  it("normalizes an explicit base URL", () => {
    expect(resolveApiBaseUrl("development", "https://example.test/api/v1///")).toBe(
      "https://example.test/api/v1"
    );
    expect(normalizeApiBaseUrl("/api/v1/")).toBe("/api/v1");
  });
});
