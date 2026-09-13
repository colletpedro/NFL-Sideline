import { describe, expect, it } from "vitest";
import { runtimeClientModule } from "../../build/runtime-client-mode";

describe("runtime data source", () => {
  it("forces the static client in production", () => {
    expect(runtimeClientModule("serve", "production")).toContain("runtimeClient.production");
    expect(runtimeClientModule("build", "staging")).toContain("runtimeClient.production");
  });

  it("uses the API client in development and test", () => {
    expect(runtimeClientModule("serve", "development")).toContain("runtimeClient.development");
    expect(runtimeClientModule("serve", "test")).toContain("runtimeClient.development");
  });
});
