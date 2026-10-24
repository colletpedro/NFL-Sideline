import { describe,it,expect,vi } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { comparisonFixture } from './real-fixture.mjs';
import { MatchupContent } from './MatchupPage';
import { EpaBlock,League,MetricValue,ThirdBlock } from './Charts';
import { coordinate,epaText,FOUNDATION_PIN,leaguePositions,linkedFacts,loadDocument,matchCalendar,permitted,rate,sideAllowed,validateDocument,type Document,type Foundation,type Metric,type Permission } from './model';
import { allowedMatchupRequest } from '../../build/matchup';
import { StaticNflDataClient } from '../../src/services/staticDataClient';

describe('pilot permissions, numbers and transport',()=>{
  it('formats exact signed decimal ratios without prematurely converting the sum to float',()=>{
    expect(rate({numerator:1,denominator:1})).toBe('100,0%');expect(rate({numerator:0,denominator:0})).toBeNull();expect(rate({numerator:0,denominator:5})).toBe('0,0%');
    expect(coordinate({numerator:'0.123456789012345678901',denominator:3})).toBe(.041152);
    expect(coordinate({numerator:'-1.00000000000000000001',denominator:3})).toBe(-.333333);
  });
  it('keeps a valid zero, zero opportunities, insufficiency and absent source distinct (synthetic only)',()=>{
    const m={descriptor:{id:'test',status:'AVAILABLE',numerator:0,denominator:5},display:{allowed:true,operation:'display',observationIds:['test'],interpretation:'OBSERVED_SAMPLE_DESCRIPTIVE'}} as Metric;
    expect(renderToStaticMarkup(<MetricValue metric={m}/>)).toContain('0,0%');
    for(const [status,phrase] of [['NO_OPPORTUNITIES','sem oportunidades elegíveis'],['INSUFFICIENT','insuficientes ou contraditórios'],['SOURCE_ABSENT','Não há fonte']] as const){const x=structuredClone(m);x.descriptor.status=status;x.descriptor.denominator=0;const html=renderToStaticMarkup(<MetricValue metric={x}/>);expect(html).toContain(phrase);expect(html).not.toContain('0,0%');}
    m.display.allowed=false;expect(renderToStaticMarkup(<MetricValue metric={m}/>)).not.toContain('0,0%');
  });
  it('ties permissions to operation and exact observation identities',()=>{
    const p:Permission={allowed:true,operation:'display',observationIds:['A'],reasonCodes:[],interpretation:'OBSERVED_SAMPLE_DESCRIPTIVE'};
    expect(permitted({...p,observationIds:['A']},'display',['A'])).toBe(true);
    expect(permitted({...p,observationIds:['A']},'sideBySide',['A'])).toBe(false);
    expect(permitted({...p,observationIds:['A']},'display',['B'])).toBe(false);
  });
  it('only accepts same-origin GET, exact route and marker with no browser-selected file',()=>{
    const headers={host:'127.0.0.1:18102','x-local-matchup':'1'};
    expect(allowedMatchupRequest('GET','/__matchup-reading/',headers,18102)).toBe(true);
    for(const [method,path,h] of [['POST','/__matchup-reading/',headers],['GET','/__matchup-reading/?path=/tmp/other',headers],['GET','/__matchup-reading/x',headers],['GET','/__matchup-reading/',{...headers,origin:'http://127.0.0.1:18101'}],['GET','/__matchup-reading/',{...headers,host:'localhost:18102'}],['GET','/__matchup-reading/',{...headers,'content-length':'1'}],['GET','/__matchup-reading/',{...headers,'transfer-encoding':'chunked'}],['GET','/__matchup-reading/',{host:headers.host}]] as const)expect(allowedMatchupRequest(method,path,h,18102)).toBe(false);
    expect(allowedMatchupRequest('GET','/__matchup-reading/',headers,18102,['Host',headers.host,'Host',headers.host])).toBe(false);
  });
  it('does not fall back when the source fails or its pin differs',async()=>{
    const fetcher=vi.fn().mockResolvedValue(new Response('{}',{status:503}));await expect(loadDocument(undefined,fetcher)).rejects.toThrow('Nenhum outro recorte');expect(fetcher).toHaveBeenCalledTimes(1);
    const wrong=vi.fn().mockResolvedValue(new Response('{}',{headers:{'X-Comparison-Bundle':'sha256:wrong'}}));await expect(loadDocument(undefined,wrong)).rejects.toThrow('identidade');expect(wrong).toHaveBeenCalledTimes(1);
  });
});
const fixture=comparisonFixture();
describe.skipIf(!fixture)('real pinned NYJ × TEN foundation (operator configured)',()=>{
  const source=()=>validateDocument(structuredClone(fixture!.data));
  const calendar=async()=>{
    const fetcher=vi.fn((path:string|URL|Request)=>Promise.resolve(new Response(JSON.stringify(String(path).includes('manifest')?fixture!.manifest:fixture!.calendar),{status:200})));
    return new StaticNflDataClient(fetcher as typeof fetch).listGames(2026);
  };
  it('joins the exact calendar identity, names, date and atomic score trio',async()=>{
    const d=source(),game=matchCalendar(await calendar(),d);expect(fixture!.marker.bundleId).toBe(FOUNDATION_PIN);expect(game).toMatchObject({gameId:'2026_01_NYJ_TEN',season:2026,week:1,gameType:'REG',gameday:'2026-09-13',awayScore:23,homeScore:10,result:-13});
    const html=renderToStaticMarkup(<MatchupContent d={d} game={game} foundation="general" onFoundation={()=>{}}/>);expect(html).toContain('New York Jets');expect(html).toContain('Tennessee Titans');expect(html).toContain('Resultado registrado');expect(html).toContain('13 de setembro de 2026');
    for(const altered of [{...game,week:2},{...game,homeTeam:game.awayTeam},{...game,gameType:'POST'}])expect(()=>matchCalendar([altered],d)).toThrow();
    expect(()=>matchCalendar([game,game],d)).toThrow();
    const noScore={...game,homeScore:null,awayScore:null,result:null};expect(renderToStaticMarkup(<MatchupContent d={d} game={noScore} foundation="general" onFoundation={()=>{}}/>)).toContain('Resultado indisponível');
  });
  it('renders all six exact EPA and denominators against the independent rational oracle, with a common scale',()=>{
    const d=source();for(const foundation of ['general','classified_pass','classified_rush'] as Foundation[]){const html=renderToStaticMarkup(<EpaBlock d={d} foundation={foundation} onFoundation={()=>{}}/>);for(const p of d.productions){const e=p.epa.find(e=>e.foundation===foundation)!,expected=fixture!.expected.epa[p.offense+'/'+foundation];expect(epaText(e)).toBe(expected.text);expect(e.descriptor.denominator).toBe(expected.denominator);expect(html).toContain(expected.text);expect(html).toContain(`${expected.denominator} jogadas com EPA válido`);}const domains=[...html.matchAll(/data-domain="([^"]+)"/g)].map(x=>x[1]);expect(domains).toHaveLength(2);expect(domains[0]).toBe(domains[1]);}
  });
  it('renders 22 exact third marks, four campaign marks and the real joint partitions',async()=>{
    const d=source(),game=matchCalendar(await calendar(),d),before=JSON.stringify(d),html=renderToStaticMarkup(<MatchupContent d={d} game={game} foundation="general" onFoundation={()=>{}}/>);
    expect([...html.matchAll(/data-third-mark="([^"]+)"/g)].map(x=>x[1])).toEqual(d.productions.flatMap(p=>p.thirdAttempts).sort((a,b)=>['short','medium','long','unknown'].indexOf(a.distance)-['short','medium','long','unknown'].indexOf(b.distance)||d.productions.findIndex(p=>p.offense===a.offense)-d.productions.findIndex(p=>p.offense===b.offense)||a.sourceOrder-b.sourceOrder).map(u=>u.id));
    expect([...html.matchAll(/data-campaign-mark="([^"]+)"/g)].map(x=>x[1])).toEqual(d.productions.flatMap(p=>p.redZoneCampaigns.map(u=>u.id)));
    expect((html.match(/data-third-mark=/g)||[])).toHaveLength(22);expect((html.match(/data-campaign-mark=/g)||[])).toHaveLength(4);
    for(const p of d.productions){expect(p.thirdAttempts.length).toBe(p.metrics.third.descriptor.denominator);for(const b of ['short','medium','long','unknown'])for(const k of ['pass','run']){const units=p.thirdAttempts.filter(u=>u.distance===b&&u.kind===k),c=p.thirdDistanceByType.find(c=>c.distance===b&&c.kind===k)!;expect(c.denominator).toBe(units.length);expect(c.numerator).toBe(units.reduce((n,u)=>n+u.converted,0));}}
    expect(html).toContain('100,0%');expect(html).toContain('1/1');expect(html).not.toContain('<select');expect(JSON.stringify(d)).toBe(before);
  });
  it('renders 32/31 true offensive points, ATL inventory and pooled rates separately',()=>{
    const d=source();for(const f of ['third','redZone'] as const){const r=d.leagueReferences[f],html=renderToStaticMarkup(<League reference={r} family={f}/>);expect((html.match(/data-league-point=/g)||[])).toHaveLength(f==='third'?32:31);expect(new Set(r.teamRateDistribution.points.map(p=>p.team)).size).toBe(r.representedTeams.length);expect(html).toContain('Taxa conjunta da amostra');expect(html).toContain(`${fixture!.expected[f].numerator}/${fixture!.expected[f].denominator}`);expect(html).toContain('não é uma amostra independente');}expect(renderToStaticMarkup(<League reference={d.leagueReferences.redZone} family="redZone"/>)).toContain('ATL — fonte presente, sem oportunidades elegíveis');
  });
  it('resolves coincident and nearby points vertically without moving their values on the horizontal axis',()=>{
    for(const ref of Object.values(source().leagueReferences)){
      const positions=leaguePositions(ref.teamRateDistribution.points);
      for(const p of positions){expect(p.x).toBeCloseTo(p.point.numerator/p.point.denominator*1000,2);for(const q of positions)if(q!==p&&Math.abs(q.x-p.x)<60)expect(q.lane).not.toBe(p.lane);}
    }
  });
  it('only publishes facts with exact linked evidence and concrete permissions, and blocks refused operations (synthetic mutations)',()=>{
    const d=source();expect(linkedFacts(d)).toHaveLength(3);d.facts[0].evidence[0].denominator++;expect(linkedFacts(d)).toHaveLength(2);
    const refused=source();refused.comparisons.third.difference.allowed=false;expect(linkedFacts(refused).some(f=>f.metric==='third')).toBe(false);
    refused.comparisons.third.sideBySide.allowed=false;expect(sideAllowed(refused,'third')).toBe(false);expect(renderToStaticMarkup(<ThirdBlock d={refused}/>)).not.toContain('data-third-mark=');
    refused.leagueReferences.redZone.permission.allowed=false;expect(renderToStaticMarkup(<League reference={refused.leagueReferences.redZone} family="redZone"/>)).not.toContain('data-league-point=');
  });
  it('rejects incompatible participants, source period and unit identities instead of substituting a slice',()=>{
    for(const mutate of [(d:Document)=>{d.productions[0].defense='NYJ';},(d:Document)=>{d.game.weeks=[1,2];},(d:Document)=>{d.productions[0].thirdAttempts[0].id='synthetic-mismatch';},(d:Document)=>{d.temporalContext.w2ContextAllowed=true;}]){const d=source();mutate(d);expect(()=>validateDocument(d)).toThrow();}
  });
});
