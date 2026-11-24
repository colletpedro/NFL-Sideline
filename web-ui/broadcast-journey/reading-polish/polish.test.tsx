import {describe,it,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {StaticRouter} from 'react-router-dom/server';
import {ReadingPolishContext} from './context';
import {AttemptSymbol,AttemptLegend} from './Attempts';
import {LeagueRows} from './LeagueRows';
import {compareObservedRates} from './rates';
import {TeamIdentityLink} from './TeamIdentityLink';
import {MatchupContent} from '../w12/Content';
import {MetricValue} from '../w12/Charts';
import {TeamPage} from '../hub-team/TeamPage';
import {Hub} from '../hub-team/Hub';
import {fixture} from '../w12/fixture.mjs';
import {teamFixture} from '../hub-team/fixture.mjs';
import {calendarGame} from '../w12/calendar';
import {teamHref} from '../hub-team/model';
import {rate,validateIndex,type Document,type Point} from '../w12/model';
const html=(child:React.ReactNode,polish=true)=>renderToStaticMarkup(<StaticRouter location="/"><ReadingPolishContext.Provider value={polish}>{child}</ReadingPolishContext.Provider></StaticRouter>);
const real=fixture(),teams=teamFixture();
const attrs=(s:string,attr:string)=>[...s.matchAll(new RegExp(`${attr}="([^"]+)"`,'g'))].map(m=>m[1]);
describe('reading polish semantic components',()=>{
 it('shares four complete final symbols; kind and conversion remain independent',()=>{
  const legend=html(<AttemptLegend/>);const combinations=new Set<string>();
  for(const kind of ['pass','run'] as const)for(const converted of [true,false]){const symbol=html(<AttemptSymbol kind={kind} converted={converted}/>);expect(legend).toContain(symbol);expect(symbol.includes('<circle')).toBe(kind==='pass');expect(symbol.includes('<rect')).toBe(kind==='run');expect(symbol.includes('m8 14 4 4 8-9')).toBe(converted);combinations.add(symbol);}
  expect(combinations.size).toBe(4);expect(attrs(legend,'data-symbol-kind')).toHaveLength(4);
 });
 it('links logo, abbreviation and full name once, with context and no score',()=>{
  const q=new URLSearchParams('week=2&q=New+York&scope=week&filter=participants&page=2');const to=teamHref(q,'NYJ');const s=html(<TeamIdentityLink team="NYJ" to={to}/>);
  expect(attrs(s,'href')).toHaveLength(1);expect(s).toContain('New York Jets');expect(s).toContain('<img');expect(s).toContain('<strong>NYJ</strong>');const target=new URL(to,'http://local');expect(target.searchParams.get('team')).toBe('NYJ');expect(target.searchParams.get('returnWeek')).toBe('2');expect(target.searchParams.get('q')).toBe('New York');expect(target.searchParams.get('page')).toBe('2');
 });
 it('orders exact observed fractions before rounding; ties use stable abbreviations',()=>{
  const p=(team:string,n:number,d:number)=>({team,numerator:n,denominator:d} as Point);
  const a=p('NYJ',1000001,3000000),b=p('TEN',1,3);expect(rate(a)).toBe(rate(b));expect(compareObservedRates(a,b)).toBeLessThan(0);
  expect([p('TEN',1,3),p('NYJ',2,6)].sort(compareObservedRates).map(p=>p.team)).toEqual(['NYJ','TEN']);
 });
});
describe.skipIf(!real||!teams)('real immutable representation across W1–2',()=>{
 it('preserves all game units, EPA values, participants and weekly reference reasons',()=>{
  let third=0,campaigns=0;
  for(const e of validateIndex(real!.index).games){const d=JSON.parse(real!.documents[e.gameId]) as Document;const component=<MatchupContent d={d} game={calendarGame(e)} foundation="general" onFoundation={()=>{}} participantHref={t=>teamHref(new URLSearchParams('week=2&q=NYJ'),t)}/>;const after=html(component),before=html(component,false);
   expect(attrs(after,'data-third-mark').sort()).toEqual(attrs(before,'data-third-mark').sort());expect(attrs(after,'data-campaign-mark').sort()).toEqual(attrs(before,'data-campaign-mark').sort());third+=attrs(after,'data-third-mark').length;campaigns+=attrs(after,'data-campaign-mark').length;
   expect(after).not.toContain('--production-color');expect(attrs(after,'data-symbol-kind')).toHaveLength(d.productions.reduce((n,p)=>n+p.thirdAttempts.length,4));
   for(const foundation of ['general','classified_pass','classified_rush'] as const){const rendering=html(<MatchupContent d={d} game={calendarGame(e)} foundation={foundation} onFoundation={()=>{}}/>);for(const p of real!.oracle.games.find(g=>g.gameId===e.gameId)!.productions){const value=p.epa.find(v=>v.foundation===foundation)!.display;expect(rendering).toContain(value.replace('<','&lt;'));const n=d.productions.find(v=>v.offense===p.team)!.epa.find(v=>v.foundation===foundation)!.descriptor.denominator;expect(rendering).toContain(`${n} jogadas com EPA válido`);}}
   for(const u of d.productions.flatMap(p=>p.thirdAttempts)){const button=after.match(new RegExp(`<button[^>]*data-third-mark="${u.id}"[^]*?</button>`))![0];expect(button).toContain(`data-symbol-kind="${u.kind}"`);expect(button).toContain(`data-symbol-converted="${!!u.converted}"`);}
   for(const family of ['third','redZone'] as const){const r=d.leagueReferences[family],s=html(<LeagueRows reference={r} family={family}/>);expect(attrs(s,'data-league-row').sort()).toEqual(r.representedTeams.slice().sort());expect(s).not.toContain('<details');expect(s).not.toContain('<button');for(const p of r.teamRateDistribution.points){const row=s.match(new RegExp(`<li[^>]*data-league-row="${p.team}"[^]*?</li>`))![0];expect(row).toContain(`${p.numerator}/${p.denominator}`);expect(row).toContain(rate(p)!);expect(row.includes('rp-league-participant')).toBe(r.participantsIncluded.includes(p.team));}for(const p of r.teamsWithoutRate)expect(attrs(s,'data-league-row')).not.toContain(p.team);expect(s).toContain(`${r.pooledRate.numerator}/${r.pooledRate.denominator}`);}
  }expect(third).toBe(787);expect(campaigns).toBe(208);
 });
 it('keeps team units, both perspectives and honest no-opportunity states',()=>{
  for(const e of teams!.index.teams){const d=teams!.docs[e.team];const component=<TeamPage d={d} q={new URLSearchParams('returnWeek=2')} foundation="general" onFoundation={()=>{}}/>;const after=html(component),before=html(component,false);for(const attr of ['data-team-third','data-team-campaign'])expect(attrs(after,attr).sort()).toEqual(attrs(before,attr).sort());expect(after).not.toContain('data-league-row');if(e.team==='ATL'){expect(after).toContain('0/0, sem taxa');expect(after).toContain('Adversários contra ATL');}}
 });
 it('makes all card identities links and keeps game actions separate at every density',()=>{
  for(const week of [1,2]){const s=html(<Hub index={teams!.matchupIndex} q={new URLSearchParams(`week=${week}&q=NYJ`)} onChange={()=>{}}/>);expect(attrs(s,'data-hub-game')).toHaveLength(16);expect((s.match(/class="rp-team-identity"/g)||[])).toHaveLength(32);expect(s).toContain('rp-scoreboard');expect(s).toContain('ht-support');expect(s).toContain('ht-compact');}
 });
 it('does not promote absence, insufficient records, zero opportunities or denied display to a percentage',()=>{
  const d=JSON.parse(real!.documents[validateIndex(real!.index).games[0].gameId]) as Document;
  for(const status of ['SOURCE_ABSENT','INSUFFICIENT','NO_OPPORTUNITIES'] as const){const m=structuredClone(d.productions[0].metrics.third);m.descriptor.status=status;m.descriptor.numerator=0;m.descriptor.denominator=0;const s=html(<MetricValue metric={m}/>);expect(s).not.toContain('rp-result');expect(s).not.toContain('%');}
  const m=structuredClone(d.productions[0].metrics.third);m.display.allowed=false;expect(html(<MetricValue metric={m}/>)).not.toContain('rp-result');
 });
 it('refuses league presentation when permission is denied, without zero rate substitute',()=>{
  const d=JSON.parse(real!.documents[validateIndex(real!.index).games[0].gameId]) as Document;const r=d.leagueReferences.redZone;r.permission.allowed=false;const s=html(<LeagueRows reference={r} family="redZone"/>);expect(s).not.toContain('data-league-row');expect(s).not.toContain('0%');
 });
});
