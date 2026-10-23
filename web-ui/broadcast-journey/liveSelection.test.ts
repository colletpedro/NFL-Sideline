import { describe, expect, it } from 'vitest';
import type { Game } from '../src/services/types';
import type { DTO, Entry } from '../local-editorial/observations/model';
import type { Archive } from './sources';
import { liveSelection, nextReadingQuery, readingPeriod } from './liveSelection';
import snapshot from '../public/data/seasons/2026.json';
import { suggestGames, searchGames } from './discoveryModel';

const game={gameId:'2026_01_BAL_IND',season:2026,week:1,gameType:'REG',awayTeam:{teamAbbr:'BAL'},homeTeam:{teamAbbr:'IND'}} as Game;
// These fixtures exercise selection only, never stand in for a validated source.
function doc(team='BAL',role='off',foundation='general',inclusive=false):DTO {
 const members=[{gameId:game.gameId,week:1,round:'REG',sourceState:'PRESENT'}];
 if(inclusive)members.push({gameId:'2026_02_NO_BAL',week:2,round:'REG',sourceState:'PRESENT'});
 return {observationId:[team,role,foundation,inclusive].join('-'),subject:{team,role,foundation},request:{season:2026,phase:'REG',period:{weeks:inclusive?[1,2]:[1]}},members,observed:{includedGameIds:members.map(m=>m.gameId)},scope:{aggregation:inclusive?'MULTI_GAME':'SINGLE_GAME'}} as DTO;
}
const archive=(...documents:DTO[])=>({documents:documents.map(d=>({d,entry:{entryId:'test'} as Entry}))} as Archive);
const games=snapshot.games.map(g=>({...g,homeTeam:snapshot.teams.find(t=>t.teamAbbr===g.homeTeamAbbr)!,awayTeam:snapshot.teams.find(t=>t.teamAbbr===g.awayTeamAbbr)!})) as Game[];
describe('direct readings retain nominal identity and period',()=>{
 it('shows the unique individual immediately without a second action',()=>{const d=doc();expect(liveSelection(game,archive(d),new URLSearchParams()).target?.d).toBe(d);});
 it('changes foundation and team in the same URL while retaining origin and filter',()=>{
  const a=archive(doc(),doc('BAL','off','classified_pass'),doc('IND','off','classified_pass'));
  const q=new URLSearchParams('season=2026&week=3&q=BAL&scope=season&filter=participants');
  const pass=nextReadingQuery(game,a,q,{play:'classified_pass'});expect(liveSelection(game,a,pass).target?.d.subject.foundation).toBe('classified_pass');
  const opponent=nextReadingQuery(game,a,pass,{team:'IND'});expect(liveSelection(game,a,opponent).target?.d.subject.team).toBe('IND');
  for(const[key,value]of q)expect(opponent.get(key)).toBe(value);expect(q.has('observation')).toBe(false);
 });
 it('retains an inclusive period through dimension changes and a reload',()=>{
  const g=doc(),i=doc('BAL','off','general',true),p=doc('BAL','def','classified_pass',true);const a=archive(g,i,p);
  const q=nextReadingQuery(game,a,new URLSearchParams(),{reading:readingPeriod(i)});
  const next=nextReadingQuery(game,a,q,{side:'def',play:'classified_pass'});
  expect(liveSelection(game,a,new URLSearchParams(next.toString())).target?.d).toBe(p);
 });
 it('does not replace a missing selected aggregate with an available individual',()=>{
  const a=archive(doc(),doc('BAL','off','general',true),doc('BAL','def'));
  const q=nextReadingQuery(game,a,new URLSearchParams(),{reading:'2026/REG/1,2'});
  const next=nextReadingQuery(game,a,q,{side:'def'});expect(next.has('observation')).toBe(false);expect(liveSelection(game,a,next).target).toBeUndefined();expect(next.get('reading')).toBe('2026/REG/1,2');
 });
 it('rejects missing, contradictory and nonparticipant nominal URLs',()=>{
  const d=doc();const a=archive(d,doc('NE'));
  for(const q of ['entry=test&observation=missing',`entry=test&observation=${d.observationId}&team=IND`,`entry=test&observation=${d.observationId}&play=classified_rush`,'entry=test&observation=NE-off-general-false'])expect(liveSelection(game,a,new URLSearchParams(q)).error).toBeTruthy();
 });
 it('refuses ambiguous sources rather than choosing their order',()=>{const d=doc();expect(liveSelection(game,archive(d,{...d,observationId:'other'}),new URLSearchParams()).error).toBeTruthy();});
 it('preserves a gap as a gap and never substitutes another period',()=>{
  const d=doc();d.members[0].sourceState='ABSENT';d.observed.includedGameIds=[];d.scope.aggregation='NO_OBSERVATION';
  expect(liveSelection(game,archive(d,doc('BAL','off','general',true)),new URLSearchParams()).target?.d).toBe(d);
 });
});
describe('one-letter suggestions use only real calendar matches',()=>{
 it('offers four matches from one letter, with the selected week first',()=>{const s=suggestGames(games,'a',2);expect(s).toHaveLength(4);expect(s.every(x=>x.game.week===2)).toBe(true);expect(s.every(x=>searchGames(games,'a').includes(x.game))).toBe(true);});
 it('recognizes initial prefixes and keeps literal NE distinct from New York',()=>{expect(suggestGames(games,'ba',1)[0].team).toBe('BAL');expect(suggestGames(games,'NE',1).every(x=>[x.game.homeTeam.teamAbbr,x.game.awayTeam.teamAbbr].includes('NE'))).toBe(true);});
 it('supports an initial V and accented aliases without inventing pairings',()=>{expect(suggestGames(games,'v',1)[0].team).toBe('MIN');expect(suggestGames(games,'Báltimore',1)[0].team).toBe('BAL');expect(suggestGames(games,'DAL LAC',1)).toEqual([]);});
 it('does not mutate calendar order and returns no suggestions for empty/missing queries',()=>{const ids=games.map(g=>g.gameId);suggestGames(games,'new',2);expect(games.map(g=>g.gameId)).toEqual(ids);expect(suggestGames(games,'',1)).toEqual([]);expect(suggestGames(games,'zzzz',1)).toEqual([]);});
});
