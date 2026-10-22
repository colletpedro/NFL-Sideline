import type { Game } from '../src/services/types';
import type { DTO } from '../local-editorial/observations/model';
import type { Archive } from './sources';
import { relation } from './relations';
import { availabilityTeams } from './discoveryModel';

export const sides = { off: 'Ataque', def: 'Defesa' };
export const foundations = { general: 'Passe + corrida', classified_pass: 'Passe', classified_rush: 'Corrida' };
export type Choice = { team: string; side: DTO['subject']['role']; play: DTO['subject']['foundation'] };
export function readChoice(game: Game, q: URLSearchParams, selected?: DTO, archive: Archive | null = null): Choice {
  const participants = [game.awayTeam.teamAbbr, game.homeTeam.teamAbbr];
  const fallback = selected && participants.includes(selected.subject.team) ? selected.subject : null;
  const team = q.get('team'), side = q.get('side'), play = q.get('play');
  return {
    team: team && participants.includes(team) ? team : fallback?.team ?? availabilityTeams(game, archive)[0] ?? [...participants].sort()[0],
    side: side === 'off' || side === 'def' ? side : fallback?.role ?? 'off',
    play: play === 'general' || play === 'classified_pass' || play === 'classified_rush' ? play : fallback?.foundation ?? 'general',
  };
}
export function choiceGroups(game: Game, archive: Archive, choice: Choice) {
  const documents = archive.documents.filter(({ d }) => d.subject.team === choice.team && d.subject.role === choice.side && d.subject.foundation === choice.play);
  return {
    primary: documents.filter(({ d }) => ['individual', 'gap'].includes(relation(game, d))),
    includes: documents.filter(({ d }) => relation(game, d) === 'includes'),
    other: documents.filter(({ d }) => relation(game, d) === 'other'),
    archive: documents.filter(({ d }) => relation(game, d) === 'archive'),
  };
}
