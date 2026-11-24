import {describe,it,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {StaticRouter} from 'react-router-dom/server';
import {RankingRedzoneContext} from './context';
import {ReadingPolishContext} from '../reading-polish/context';
import {observedPositions} from './positions';
import {RankingLeague} from './RankingLeague';
import {CampaignSymbol,CampaignLegend,CampaignMark} from './Campaigns';
import {MatchupContent} from '../w12/Content';
import {TeamPage} from '../hub-team/TeamPage';
import {fixture} from '../w12/fixture.mjs';
import {teamFixture} from '../hub-team/fixture.mjs';
import {positionOracle} from './fixture.mjs';
import {calendarGame} from '../w12/calendar';
import {validateIndex,type Document,type Point,type Campaign,rate} from '../w12/model';
const html=(node:React.ReactNode,enabled=true)=>renderToStaticMarkup(<StaticRouter location="/"><ReadingPolishContext.Provider value={true}><RankingRedzoneContext.Provider value={enabled}>{node}</RankingRedzoneContext.Provider></ReadingPolishContext.Provider></StaticRouter>);
const attrs=(s:string,a:string)=>[...s.matchAll(new RegExp(`${a}="([^"]+)"`,'g'))].map(m=>m[1]);
const real=fixture(),teams=teamFixture();
const point=(team:string,numerator:number,denominator:number)=>({team,numerator,denominator,status:'AVAILABLE'} as Point);
describe('shared observed positions and campaign language',()=>{
 it('uses competition positions, equivalent fractions and unrounded comparisons',()=>{
  const rows=observedPositions([point('A',1,1),point('B',1,3),point('C',2,6),point('D',0,2)]);expect(rows.map(r=>r.position)).toEqual([1,2,2,4]);
  const high=point('A',1000001,3000000),low=point('B',1,3);expect(rate(high)).toBe(rate(low));expect(observedPositions([low,high]).map(r=>[r.point.team,r.position])).toEqual([['A',1],['B',2]]);
  expect(observedPositions([point('A',2,2),point('B',1,1),point('C',3,3),point('D',1,2)]).map(r=>r.position)).toEqual([1,1,1,4]);
  for(const p of [point('A',0,0),{...point('A',0,1),status:'INSUFFICIENT'} as Point])expect(()=>observedPositions([p])).toThrow();
 });
 it('shares the final SVG between legends and campaigns, preserving nine different outcomes and fallback',()=>{
  const values=['TOUCHDOWN','FIELD_GOAL','MISSED_FIELD_GOAL','TURNOVER','OPPONENT_TOUCHDOWN','DOWNS','PUNT','END_HALF_GAME','SAFETY','UNKNOWN_OUTCOME'];const symbols=new Set<string>();
  const legend=html(<CampaignLegend outcomes={values}/>);
  for(const outcome of values){const symbol=html(<CampaignSymbol outcome={outcome}/>);expect(legend).toContain(symbol);symbols.add(symbol.replace(/data-outcome-symbol="[^"]+"/,''));const u={id:'game:drive:6',outcome,offense:'NYJ',defense:'TEN',week:2,fixedDrive:6} as Campaign;
   const mark=html(<CampaignMark unit={u} label="NYJ com a bola" scope="team" selected={false} onSelect={()=>{}}/>);expect(mark).toContain(symbol);expect(mark).toContain('W2');expect(attrs(mark,'data-team-campaign')).toEqual([u.id]);expect(mark).toContain('NYJ contra TEN');}
  expect(symbols.size).toBe(values.length);
 });
});
describe.skipIf(!real||!teams)('immutable collection representation with compact reference',()=>{
 it('checks all full-universe positions against independent Fraction oracle, with two participants in away/home order',()=>{
  for(const e of validateIndex(real!.index).games){const d=JSON.parse(real!.documents[e.gameId]) as Document;
   for(const family of ['third','redZone'] as const){const r=d.leagueReferences[family],oracle=positionOracle.games[e.gameId][family];const s=html(<RankingLeague reference={r} family={family} participants={[e.away,e.home]}/>);const summary=s.match(/data-ranking-scope="summary"[^]*?<\/ul>/)![0];expect(attrs(summary,'data-ranking-team')).toEqual([e.away,e.home]);expect(attrs(s,'data-position').filter(p=>p!=='none')).toHaveLength(oracle.n+[e.away,e.home].filter(t=>oracle.positions[t]).length);
    const full=s.match(/data-ranking-scope="full"[^]*?<\/ul>/)![0];expect(attrs(full,'data-ranking-team').sort()).toEqual(r.representedTeams.slice().sort());
    for(const p of r.teamRateDistribution.points){const row=full.match(new RegExp(`<li[^>]*data-ranking-team="${p.team}"[^]*?</li>`))![0];expect(attrs(row,'data-position')).toEqual([String(oracle.positions[p.team])]);expect(row).toContain(`${p.numerator} de ${p.denominator}`);if([e.away,e.home].includes(p.team)){const compactRow=summary.match(new RegExp(`<li[^>]*data-ranking-team="${p.team}"[^]*?</li>`))![0];expect(attrs(compactRow,'data-rate-x')).toEqual(attrs(row,'data-rate-x'));expect(attrs(compactRow,'data-position')).toEqual(attrs(row,'data-position'));}}
    expect(s).toContain('aria-expanded="false"');expect(s).toContain('inert=""');expect(s).toContain('aria-hidden="true"');expect(s).toContain(`${r.pooledRate.numerator}/${r.pooledRate.denominator}`);
   }
  }
 });
 it('preserves every campaign ID/order/outcome, third attempt and metric in games and both team perspectives',()=>{
  let n=0;const inventory:Record<string,number>={};
  for(const e of validateIndex(real!.index).games){const d=JSON.parse(real!.documents[e.gameId]) as Document;const component=<MatchupContent d={d} game={calendarGame(e)} foundation="general" onFoundation={()=>{}}/>;const before=html(component,false),after=html(component);
   expect(attrs(after,'data-campaign-mark')).toEqual(attrs(before,'data-campaign-mark'));expect(attrs(after,'data-third-mark')).toEqual(attrs(before,'data-third-mark'));const units=d.productions.flatMap(p=>p.redZoneCampaigns);expect(attrs(after,'data-campaign-outcome')).toEqual(units.map(u=>u.outcome));for(const u of units){inventory[u.outcome]=(inventory[u.outcome]??0)+1;n++;}expect(after).not.toContain('data-redzone-epa');
  }expect(n).toBe(208);expect(inventory).toEqual(positionOracle.campaignOutcomes);
  for(const e of teams!.index.teams){const d=teams!.docs[e.team],component=<TeamPage d={d} q={new URLSearchParams('returnWeek=2')} foundation="general" onFoundation={()=>{}}/>;const before=html(component,false),after=html(component);expect(attrs(after,'data-team-campaign')).toEqual(attrs(before,'data-team-campaign'));expect(attrs(after,'data-campaign-outcome')).toEqual(d.productions.flatMap(p=>p.redZoneCampaigns.map(u=>u.outcome)));expect(after).not.toContain('data-ranking-scope');}
 });
 it('keeps participants without a rate unpositioned, preserves valid 0%, and respects refusal',()=>{
  const d=JSON.parse(real!.documents['2026_01_ATL_PIT']) as Document;const s=html(<RankingLeague reference={d.leagueReferences.redZone} family="redZone" participants={['ATL','PIT']}/>);const summary=s.match(/data-ranking-scope="summary"[^]*?<\/ul>/)![0],atl=summary.match(/<li[^>]*data-ranking-team="ATL"[^]*?<\/li>/)![0];expect(attrs(atl,'data-position')).toEqual(['none']);expect(atl).not.toContain('%');expect(atl).not.toContain('data-rate-x');expect(atl).toContain('0/0');
  for(const status of ['SOURCE_ABSENT','INSUFFICIENT'] as const){const missing=structuredClone(d.leagueReferences.redZone);missing.inventory.find(p=>p.team==='ATL')!.status=status;missing.teamsWithoutRate.find(p=>p.team==='ATL')!.status=status;const rendering=html(<RankingLeague reference={missing} family="redZone" participants={['ATL','PIT']}/>);const row=rendering.match(/<li[^>]*data-ranking-team="ATL"[^]*?<\/li>/)![0];expect(row).not.toContain('0/0');expect(row).not.toContain('data-rate-x');expect(attrs(row,'data-position')).toEqual(['none']);}
  const denied=structuredClone(d.leagueReferences.redZone);denied.permission.allowed=false;expect(html(<RankingLeague reference={denied} family="redZone" participants={['ATL','PIT']}/>)).not.toContain('data-position=');
  const ne=JSON.parse(real!.documents['2026_01_NE_SEA']) as Document;const zero=observedPositions(ne.leagueReferences.redZone.teamRateDistribution.points).find(e=>e.point.team==='SEA')!;expect(zero.position).toBeGreaterThan(0);expect(zero.point.numerator).toBe(0);
 });
});
