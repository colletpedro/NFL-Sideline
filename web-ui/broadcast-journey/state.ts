export function journeyHref(base: URLSearchParams, change: Record<string, string | null>) {
  const next = new URLSearchParams(base);
  for (const [key, value] of Object.entries(change)) { if (value === null) next.delete(key); else next.set(key, value); }
  return `/?${next}`;
}
export const calendarChange = { game: null, entry: null, observation: null, details: null, composition: null, reading: null };
export const gameChange = { entry: null, observation: null, details: null, composition: null, reading: null };
