import type { Game } from '../src/services/types';
import type { DTO } from '../local-editorial/observations/model';
import type { Archive } from './sources';
import { readChoice, type Choice } from './choice';
import { relation } from './relations';
import { journeyHref } from './state';

export const readingPeriod = (d: DTO) => `${d.request.season}/${d.request.phase}/${d.request.period.weeks.join(',')}`;
export type LiveSelection = { choice: Choice; period: string; target?: Archive['documents'][number]; error?: string };
export function matchingReadings(game: Game, archive: Archive, choice: Choice, period: string) {
  return archive.documents.filter(({ d }) => d.subject.team === choice.team && d.subject.role === choice.side && d.subject.foundation === choice.play &&
    (period === 'game' ? ['individual', 'gap'].includes(relation(game, d)) : readingPeriod(d) === period && relation(game, d) !== 'incompatible'));
}
// Nominal URLs are a boundary: a bad ID or contradictory dimension never falls back.
export function liveSelection(game: Game, archive: Archive, q: URLSearchParams): LiveSelection {
  const nominal = q.has('entry') || q.has('observation');
  const named = nominal ? archive.documents.find(x => x.entry.entryId === q.get('entry') && x.d.observationId === q.get('observation')) : undefined;
  const choice = readChoice(game, q, named?.d, archive);
  const namedPeriod = named && ['individual', 'gap'].includes(relation(game, named.d)) ? 'game' : named ? readingPeriod(named.d) : 'game';
  const period = q.get('reading') ?? namedPeriod;
  if (nominal && !named) return { choice, period, error: 'Observação não encontrada. Escolha um recorte disponível para continuar.' };
  if (named && (relation(game, named.d) === 'incompatible' || named.d.subject.team !== choice.team || named.d.subject.role !== choice.side || named.d.subject.foundation !== choice.play || period !== namedPeriod)) {
    return { choice, period, error: 'A observação da URL não corresponde ao time, fundamento ou período selecionado.' };
  }
  if (named) return { choice, period, target: named };
  const matches = matchingReadings(game, archive, choice, period);
  return matches.length > 1 ? { choice, period, error: 'Há mais de uma fonte para este recorte. Nenhuma foi escolhida automaticamente.' } : { choice, period, target: matches[0] };
}
// Keep the current period while changing dimensions; absence stays absence.
export function nextReadingQuery(game: Game, archive: Archive, q: URLSearchParams, change: Record<string, string>) {
  const current = liveSelection(game, archive, q);
  const next = new URLSearchParams(q);
  const choice = { ...current.choice, ...change } as Choice;
  const period = change.reading ?? current.period;
  for (const [key, value] of Object.entries({ ...choice, ...change, reading: period })) if (['team', 'side', 'play', 'reading'].includes(key)) next.set(key, value);
  next.delete('entry'); next.delete('observation');
  const matches = matchingReadings(game, archive, choice, period);
  if (matches.length === 1) { next.set('entry', matches[0].entry.entryId); next.set('observation', matches[0].d.observationId); }
  return new URLSearchParams(journeyHref(next, {}).slice(2));
}
