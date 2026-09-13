export function runtimeClientModule(command: string, mode: string): string {
  return command === "build" || mode === "production"
    ? "/src/services/runtimeClient.production.ts"
    : "/src/services/runtimeClient.development.ts";
}
