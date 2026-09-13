import { describe, expect, it } from "vitest";
import { normalizeApiBaseUrl, resolveApiBaseUrl } from "./apiDataClient";

describe("API base URL", () => {
  it("uses localhost for local development", () => {
    expect(resolveApiBaseUrl("development")).toBe(
      "http://localhost:8080/api/v1"
    );
  });

  it("normalizes an explicit base URL", () => {
    expect(resolveApiBaseUrl("development", "https://example.test/api/v1///")).toBe(
      "https://example.test/api/v1"
    );
    expect(normalizeApiBaseUrl("/api/v1/")).toBe("/api/v1");
  });
});
