// Keep the approved −0.20 … +0.40 range, extending in 0.20 increments when needed.
// Every selection uses a common, signed axis for its participating series. No clipping.
export function epaScale(values: (number | null)[]) {
  const finite = values.filter((v): v is number => v !== null && Number.isFinite(v));
  const min = Number((Math.floor((Math.min(-.2, ...finite) + 1e-10) / .2) * .2).toFixed(3));
  const max = Number((Math.ceil((Math.max(.4, ...finite) - 1e-10) / .2) * .2).toFixed(3));
  const ticks = Array.from({ length: Math.round((max - min) / .2) + 1 }, (_, i) => Number((min + i * .2).toFixed(3)));
  return { min, max, ticks, position: (value: number) => (value - min) / (max - min) * 100 };
}

// Label only the domain bounds and zero; retain every grid tick and bar position.
export function epaAxisLabels(scale: ReturnType<typeof epaScale>) {
  return scale.ticks.filter(value => value === scale.min || value === 0 || value === scale.max);
}
