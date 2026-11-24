import type { Summary } from './model';
export const period = (s: Summary) => `${s.request.season} · ${s.request.phase} · ${s.request.origin === 'HISTORICAL_REFERENCE' ? 'Referência histórica' : 'Arquivo da temporada'} · semanas ${s.request.period.weeks.join(', ')}`;
export const order = (a: Summary, b: Summary) => a.subject.team.localeCompare(b.subject.team) ||
  (a.subject.role === b.subject.role ? 0 : a.subject.role === 'off' ? -1 : 1) ||
  (['general', 'classified_pass', 'classified_rush'].indexOf(a.subject.foundation) - ['general', 'classified_pass', 'classified_rush'].indexOf(b.subject.foundation)) || period(a).localeCompare(period(b)) || a.observationId.localeCompare(b.observationId);
export function chooseAvailable(list: Summary[], selected?: Summary) {
  const sameRole = list.filter(s => s.subject.role === selected?.subject.role);
  const roles = sameRole.length ? sameRole : list;
  const sameFoundation = roles.filter(s => s.subject.foundation === selected?.subject.foundation);
  const foundations = sameFoundation.length ? sameFoundation : roles;
  return (selected && foundations.find(s => period(s) === period(selected))) || [...foundations].sort(order)[0];
}
