import { describe, expect, it } from 'vitest';
import { epaAxisLabels, epaScale } from './chartScale';

const domains: (number | null)[][] = [[null], [-.1, .06], [.5, .25], [-.3, null], [-.8, 1], [0, 0]];

describe('EPA axis presentation', () => {
  it('preserves zero and both bounds, in order and inside the scale domain', () => {
    for (const values of domains) {
      const scale = epaScale(values), labels = epaAxisLabels(scale);
      expect(labels).toContain(0);
      expect(labels[0]).toBe(scale.min);
      expect(labels[labels.length - 1]).toBe(scale.max);
      expect(new Set(labels).size).toBe(labels.length);
      expect(labels.every((value, index) => value >= scale.min && value <= scale.max && (index === 0 || value > labels[index - 1]))).toBe(true);
      expect(labels.every(value => scale.ticks.includes(value))).toBe(true);
    }
  });

  it('does not mutate the domain, grid ticks or positions of values and zero', () => {
    for (const values of domains) {
      const scale = epaScale(values), positions = [...values, 0, scale.min, scale.max].filter((value): value is number => value !== null).map(value => [value, scale.position(value)]);
      const before = { min: scale.min, max: scale.max, ticks: [...scale.ticks] };
      Object.freeze(scale.ticks);
      Object.freeze(scale);
      epaAxisLabels(scale);
      expect({ min: scale.min, max: scale.max, ticks: scale.ticks }).toEqual(before);
      for (const [value, position] of positions) expect(scale.position(value)).toBe(position);
      expect(scale.position(scale.min)).toBe(0);
      expect(scale.position(scale.max)).toBe(100);
    }
  });
});
