/**
 * Team accent colors — used only as tiny contextual indicators on the
 * dark app surface. Official primaries are darkened/lightened where
 * needed to stay legible at small sizes on #101214.
 */
export const TEAM_COLORS: Record<string, string> = {
  ARI: "#A3324A",
  ATL: "#A71930",
  BAL: "#8A6FE0",
  BUF: "#3D7BD9",
  CAR: "#0085CA",
  CHI: "#4A7EDB",
  CIN: "#FB4F14",
  CLE: "#C9793F",
  DAL: "#3D7AE8",
  DEN: "#F2684E",
  DET: "#23A2E0",
  GB: "#5FAF43",
  HOU: "#2E77B0",
  IND: "#3D82E0",
  JAX: "#17A0C9",
  KC: "#E0474F",
  LAC: "#2FA3E0",
  LAR: "#5B7FE0",
  LV: "#A9B0BA",
  MIA: "#1FBFB9",
  MIN: "#8B6FE0",
  NE: "#4A6FA8",
  NO: "#E3C878",
  NYG: "#3D6FE0",
  NYJ: "#3DBE8E",
  PHI: "#45A29B",
  PIT: "#F5BE27",
  SF: "#D95656",
  SEA: "#3391E0",
  TB: "#E23B45",
  TEN: "#4A74D0",
  WAS: "#C05A68",
};

export function teamColor(abbr: string | null | undefined): string {
  if (abbr && TEAM_COLORS[abbr]) return TEAM_COLORS[abbr];
  return "#9AA0A8";
}