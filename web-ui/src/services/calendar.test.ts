import { describe, expect, it } from "vitest";
import { initialWeek } from "./calendar";

const games = [
  { week: 2, gameday: "2029-09-20" }, { week: 1, gameday: "2029-09-10" },
  { week: 2, gameday: "2029-09-24" }, { week: 1, gameday: "2029-09-14" },
  { week: 18, gameday: "2030-01-06" },
];

describe("initial calendar week", () => {
  it.each([
    ["2029-08-01", 1], ["2029-09-10", 1], ["2029-09-12", 1], ["2029-09-14", 1],
    ["2029-09-15", 2], ["2029-09-24", 2], ["2029-12-30", 18], ["2030-02-01", 18],
  ])("selects %s without odds or analyses", (date, expected) => {
    expect(initialWeek(games, new Date(`${date}T23:59:59Z`))).toBe(expected);
  });
  it("handles empty schedules and missing dates deterministically", () => {
    expect(initialWeek([], new Date("2029-09-10"))).toBeNull();
    expect(initialWeek([{ week: 1, gameday: null }], new Date("2029-09-10"))).toBe(1);
    expect(initialWeek([...games, { week: 3, gameday: null }], new Date("2029-09-15"))).toBe(2);
  });
});
