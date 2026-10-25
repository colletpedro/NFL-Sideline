import {describe,it,expect,vi} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {StaticRouter} from 'react-router-dom/server';
import {Hub} from './Hub';
import {TeamPage} from './TeamPage';
import {backHref,gameHref,loadTeam,metricText,pairAllowed,RequestGate,resolveTeam,teamFacts,teamHref,validateContext,validateTeamDocument,validateTeamIndex,weekHref} from './model';
import {teamFixture} from './fixture.mjs';
import {suggestTeams,searchGames} from '../discoveryModel';
import {calendarGame} from '../w12/calendar';
import {allowedTeamRequest,freezeTeam} from '../../build/team';
const fixture=teamFixture();const html=(node:React.ReactNode)=>renderToStaticMarkup(<StaticRouter location="/">{node}</StaticRouter>);
describe('hub/team routes and operations',()=>{
 it('retains search/filter/week context across team and a game from another week',()=>{
  const q=new URLSearchParams('season=2026&week=1&q=NYJ&scope=season&filter=participants&page=2');
  const team=new URLSearchParams(teamHref(q,'NYJ').slice(2));expect(team.get('week')).toBeNull();expect(team.get('returnWeek')).toBe('1');
  const game=new URLSearchParams(gameHref(team,{gameId:'2026_02_NYJ_BUF',season:2026,phase:'REG',week:2,away:'NYJ',home:'BUF',gameday:null,awayScore:null,homeScore:null,result:null,calendarSourceHash:'x',calendarOrigin:'x'}).slice(2));
  expect(game.get('week')).toBe('2');expect(backHref(game)).toBe(backHref(q));expect(backHref(game)).toContain('q=NYJ');expect(backHref(game)).toContain('page=2');expect(weekHref(q,2)).toContain('week=2');
  for(const x of ['season=2025','phase=POST','returnWeek=3','team=BAL&team=ATL'])expect(()=>validateContext(new URLSearchParams(x))).toThrow();expect(backHref(new URLSearchParams('week=99'))).toContain('week=1');
 });
 it('rejects cross-origin, query, browser file paths and non-GET requests',()=>{
  const h={host:'127.0.0.1:18105','x-local-team-w12':'1'};expect(allowedTeamRequest('GET','/__team-w12/BAL',h,18105)).toBe(true);
  for(const [method,path,headers] of [['POST','/__team-w12/',h],['GET','/__team-w12/?path=/tmp/x',h],['GET','/__team-w12/BAL/x',h],['GET','/__team-w12/',{...h,origin:'http://127.0.0.1:18104'}],['GET','/__team-w12/',{...h,'content-length':'2'}]] as const)expect(allowedTeamRequest(method,path,headers,18105)).toBe(false);
 });
 it('does not allow late responses to become current after rapid entity changes',async()=>{
  const gate=new RequestGate(),first=gate.begin();let deliver!:(value:string)=>void;const slow=new Promise<string>(r=>{deliver=r;});let visible='';
  const old=slow.then(v=>{if(gate.current(first))visible=v;});const second=gate.begin();if(gate.current(second))visible='ATL';deliver('BAL');await old;expect(visible).toBe('ATL');gate.cancel();expect(gate.current(second)).toBe(false);
 });
});
describe.skipIf(!fixture)('real 32 team documents and identity',()=>{
 const data=(t='BAL')=>validateTeamDocument(structuredClone(fixture!.docs[t]),fixture!.index.teams.find(e=>e.team===t)!);
 it('renders all 32 teams, both perspectives, exact EPA/denominators and real units',()=>{
  const i=validateTeamIndex(fixture!.index);expect(i.teams).toHaveLength(32);
  for(const e of i.teams){const d=data(e.team);for(const foundation of ['general','classified_pass','classified_rush'] as const){const view=html(<TeamPage d={d} q={new URLSearchParams('returnWeek=1')} foundation={foundation} onFoundation={()=>{}}/>);expect(view).toContain(`data-team-identity="${e.team}"`);for(const p of d.productions){const metric=p.epa.find(e=>e.foundation===foundation)!;expect(metricText(metric,true)).toBe(fixture!.oracle.rounding[e.team+'/'+p.perspective+'/'+foundation]);expect(view).toContain(metricText(metric,true)!.replace('<','&lt;'));expect(view).toContain(`${metric.descriptor.denominator} jogadas com EPA válido`);}expect((view.match(/data-team-third=/g)||[])).toHaveLength(d.productions.reduce((n,p)=>n+p.thirdAttempts.length,0));expect((view.match(/data-team-campaign=/g)||[])).toHaveLength(d.productions.reduce((n,p)=>n+p.redZoneCampaigns.length,0));expect(view).not.toContain('<select');}
   expect(d.games.map(g=>g.gameId)).toEqual(e.gameIds);
  }
 });
 it('shows ATL source-present zero opportunities without 0%, preserving opponent production',()=>{
  const d=data('ATL'),view=html(<TeamPage d={d} q={new URLSearchParams()} foundation="general" onFoundation={()=>{}}/>);
  expect(d.productions[0].metrics.redZone.descriptor.status).toBe('NO_OPPORTUNITIES');expect(view).toContain('0/0, sem taxa');expect(view).toContain('Adversários contra ATL');expect(pairAllowed(d,'redZone')).toBe(false);
 });
 it('keeps every weekly matchup visible in the hub and offers separate team/match destinations',()=>{
  for(const w of [1,2]){const view=html(<Hub index={fixture!.matchupIndex} q={new URLSearchParams(`week=${w}`)} onChange={()=>{}}/>);expect((view.match(/data-hub-game=/g)||[])).toHaveLength(16);expect(view).toContain('ht-feature');expect(view).toContain('ht-support');expect(view).toContain('ht-compact');expect(view).toContain('view=team-w12');expect(view).toContain('view=matchup-w12');expect(view).not.toMatch(/<a[^>]*>[^]*<a[^>]*>[^]*<\/a><\/a>/);}
 });
 it('suggests first-letter teams and games, distinguishes NYJ/NYG and LA/LAC without silent destination substitution',()=>{
  const games=fixture!.matchupIndex.games.map(calendarGame),teams=[...new Map(games.flatMap(g=>[g.awayTeam,g.homeTeam]).map(t=>[t.teamAbbr,t])).values()];
  expect(suggestTeams(teams,'N').length).toBeGreaterThan(0);expect(searchGames(games,'N').length).toBeGreaterThan(0);
  expect(suggestTeams(teams,'NYJ').map(t=>t.teamAbbr)).toEqual(['NYJ']);expect(suggestTeams(teams,'New York').map(t=>t.teamAbbr).sort()).toEqual(['NYG','NYJ']);expect(suggestTeams(teams,'LA').map(t=>t.teamAbbr)).toEqual(['LA']);expect(suggestTeams(teams,'LAC').map(t=>t.teamAbbr)).toEqual(['LAC']);
 });
 it('keeps missing/insufficient aggregate and refused operation separate from valid component values (synthetic only)',()=>{
  for(const status of ['SOURCE_ABSENT','INSUFFICIENT'] as const){const d=data();const m=d.productions[0].metrics.third;m.descriptor.status=status;m.descriptor.numerator=null;m.descriptor.denominator=null;m.aggregation.allowed=false;m.display.allowed=false;d.comparisons.third.sideBySide.allowed=false;
   const view=html(<TeamPage d={d} q={new URLSearchParams()} foundation="general" onFoundation={()=>{}}/>);expect(metricText(m)).toBeNull();expect(pairAllowed(d,'third')).toBe(false);for(const c of m.components)expect(view).toContain(`${c.descriptor.numerator}/${c.descriptor.denominator}`);expect(teamFacts(d).some(f=>f.observationId===m.descriptor.id)).toBe(false);
  }
  const d=data();d.comparisons.general.sideBySide.allowed=false;expect(pairAllowed(d,'general')).toBe(false);expect(html(<TeamPage d={d} q={new URLSearchParams()} foundation="general" onFoundation={()=>{}}/>)).not.toContain('data-domain=');
 });
 it('rejects incompatible identifiers, periods, source and duplicate units',()=>{
  const i=validateTeamIndex(fixture!.index);for(const q of ['team=BAD','team=BAL&week=1','team=BAL&weeks=2','team=BAL&season=2025','team=BAL&game=other'])expect(()=>resolveTeam(i,new URLSearchParams(q))).toThrow();
  const d=data();d.productions[0].thirdAttempts[0].defense='BAD';d.productions[0].thirdAttempts[0].gameId='other';expect(()=>validateTeamDocument(d,i.teams.find(t=>t.team==='BAL')!)).toThrow();
  const duplicate=data();duplicate.productions[0].metrics.third.descriptor.unitIds.push(duplicate.productions[0].metrics.third.descriptor.unitIds[0]);expect(()=>validateTeamDocument(duplicate,i.teams.find(t=>t.team==='BAL')!)).toThrow();const foreign=structuredClone(fixture!.index);foreign.sourceCollection='sha256:'+'0'.repeat(64);expect(()=>validateTeamIndex(foreign)).toThrow();
  const bytes=JSON.stringify(fixture!.index);expect(()=>freezeTeam({bundleId:'wrong',index:bytes,documents:{}})).toThrow();
 });
 it('fails team source independently without fetching a fixture or another team',async()=>{
  const fetcher=vi.fn().mockResolvedValue(new Response('{}',{status:503}));await expect(loadTeam(fixture!.index.teams[0],undefined,fetcher)).rejects.toThrow('não puderam ser validados');expect(fetcher).toHaveBeenCalledTimes(1);
 });
});
