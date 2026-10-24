import {describe,it,expect,vi} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {fixture} from './fixture.mjs';
import {COLLECTION_PIN,ENDPOINT,calendarHref,epaText,linkedFacts,loadDocument,loadIndex,matchupHref,rate,resolveEntry,validateDocument,validateIndex,type Metric} from './model';
import {calendarGame} from './calendar';
import {MatchupContent} from './Content';
import {EpaBlock,MetricValue,RedZoneBlock,ThirdBlock} from './Charts';
import {allowedW12Request,freezeW12} from '../../build/w12';

it('keeps zero rates and all four availability states distinct (synthetic only)',()=>{
  const m={descriptor:{id:'synthetic',numerator:0,denominator:5,status:'AVAILABLE'},display:{allowed:true,operation:'display',observationIds:['synthetic'],interpretation:'OBSERVED_SAMPLE_DESCRIPTIVE'}} as Metric;
  expect(renderToStaticMarkup(<MetricValue metric={m}/>)).toContain('0,0%');
  for(const [status,text] of [['NO_OPPORTUNITIES','sem oportunidades'],['INSUFFICIENT','insuficientes'],['SOURCE_ABSENT','Não há fonte']] as const){const x=structuredClone(m);x.descriptor.status=status;x.descriptor.denominator=0;const h=renderToStaticMarkup(<MetricValue metric={x}/>);expect(h).toContain(text);expect(h).not.toContain('0,0%');}
  expect(rate({numerator:0,denominator:0})).toBeNull();
});
it('restricts routes, methods, headers, authority and body explicitly',()=>{
  const h={host:'127.0.0.1:18104','x-local-matchup-w12':'1'};
  expect(allowedW12Request('GET',ENDPOINT,h,18104)).toBe(true);
  for(const url of [ENDPOINT+'?path=/tmp/file',ENDPOINT+'../file',ENDPOINT+'2026_01_NYJ_TEN/child',ENDPOINT+'2026_01_NYJ_TEN?x=1'])expect(allowedW12Request('GET',url,h,18104)).toBe(false);
  for(const method of ['POST','PUT','OPTIONS','HEAD'])expect(allowedW12Request(method,ENDPOINT,h,18104)).toBe(false);
  for(const extra of [{origin:'null'},{origin:'http://127.0.0.1:18103'},{host:'localhost:18104'},{'content-length':'1'},{expect:'100-continue'},{'transfer-encoding':'chunked'},{'x-local-matchup-w12':''}])expect(allowedW12Request('GET',ENDPOINT,{...h,...extra},18104)).toBe(false);
  expect(allowedW12Request('GET',ENDPOINT,h,18104,['Host',h.host,'Host',h.host])).toBe(false);
});
it('fails closed without fetching a replacement source',async()=>{
  const f=vi.fn().mockResolvedValue(new Response('{}',{status:503}));await expect(loadIndex(undefined,f)).rejects.toThrow('Nenhum outro jogo');expect(f).toHaveBeenCalledTimes(1);
  const network=vi.fn().mockRejectedValue(new TypeError('Failed to fetch'));await expect(loadIndex(undefined,network)).rejects.toThrow('Fonte local indisponível');expect(network).toHaveBeenCalledTimes(1);
});
const real=fixture();
describe.skipIf(!real)('all 32 real matchups',()=>{
  const index=()=>validateIndex(structuredClone(real!.index));
  const doc=(id:string)=>validateDocument(JSON.parse(real!.documents[id]),index().games.find(e=>e.gameId===id)!);
  it('validates all documents, exact calendar identity, all six EPA, marks, weeks and facts',()=>{
    for(const e of index().games){const d=doc(e.gameId),g=calendarGame(e),h=renderToStaticMarkup(<MatchupContent d={d} game={g} foundation="general" onFoundation={()=>{}}/>);
      expect(h).toContain(`${e.away} × ${e.home}`);expect(h).toContain(`Semana ${e.week}`);expect(h).toContain(`W${e.week}`);expect(h).not.toContain('<select');expect(h).not.toContain('TD(s)');
      expect((h.match(/data-third-mark=/g)||[])).toHaveLength(d.productions.reduce((n,p)=>n+p.thirdAttempts.length,0));
      expect((h.match(/data-campaign-mark=/g)||[])).toHaveLength(d.productions.reduce((n,p)=>n+p.redZoneCampaigns.length,0));
      expect(linkedFacts(d)).toHaveLength(d.facts.length);
      for(const foundation of ['general','classified_pass','classified_rush'] as const){const chart=renderToStaticMarkup(<EpaBlock d={d} foundation={foundation} onFoundation={()=>{}}/>);for(const p of d.productions){const x=p.epa.find(x=>x.foundation===foundation)!;const oracle=real!.oracle.games.find(g=>g.gameId===e.gameId)!.productions.find(t=>t.team===p.offense)!.epa.find(x=>x.foundation===foundation)!;expect(epaText(x)).toBe(oracle.display);expect(chart).toContain(oracle.display.replace(/</g,"&lt;"));expect(chart).toContain(`${x.descriptor.denominator} jogadas com EPA válido`);}const domains=[...chart.matchAll(/data-domain="([^"]+)"/g)].map(x=>x[1]);expect(domains).toHaveLength(2);expect(domains[0]).toBe(domains[1]);}
      expect(d.leagueReferences.third.pooledRate).toMatchObject(e.week===1?{numerator:154,denominator:377}:{numerator:169,denominator:410});
      expect(d.leagueReferences.redZone.pooledRate).toMatchObject(e.week===1?{numerator:70,denominator:108}:{numerator:54,denominator:100});
    }
  });
  it('does not discard permitted individual data when comparison is refused or the other EPA is missing (synthetic mutation)',()=>{
    const d=doc('2026_01_NYJ_TEN');d.comparisons.third.sideBySide.allowed=false;d.comparisons.redZone.sideBySide.allowed=false;
    expect(renderToStaticMarkup(<ThirdBlock d={d}/>)).toContain('data-third-mark=');expect(renderToStaticMarkup(<RedZoneBlock d={d}/>)).toContain('data-campaign-mark=');
    const first=d.productions[0].epa[0],second=d.productions[1].epa[0];first.descriptor.status='SOURCE_ABSENT';first.display.allowed=false;first.originalObservation.values.epa=null;
    const h=renderToStaticMarkup(<EpaBlock d={d} foundation="general" onFoundation={()=>{}}/>);expect(h).toContain('Não há fonte');expect(h).toContain(epaText(second)!);expect(h).not.toContain('data-domain=');
    for(const state of ['INSUFFICIENT','SOURCE_ABSENT'] as const){d.productions[0].metrics.third.descriptor.status=state;expect(renderToStaticMarkup(<ThirdBlock d={d}/>)).toContain('data-third-mark=');}
  });
  it('keeps no-opportunity attacks separate from their valid opponent in the real collection',()=>{
    const d=doc('2026_01_ATL_PIT'),h=renderToStaticMarkup(<RedZoneBlock d={d}/>);expect(h).toContain('sem oportunidades elegíveis');expect(h).toContain('data-campaign-mark=');expect(linkedFacts(d).some(f=>f.metric==='redZone')).toBe(false);
  });
  it('rejects unknown/incompatible URLs and preserves return filters across matchups',()=>{
    const i=index(),e=i.games[20];expect(resolveEntry(i,new URLSearchParams({game:e.gameId}))).toEqual(e);
    for(const q of [{game:'unknown'},{game:e.gameId,season:'2025'},{game:e.gameId,week:String(e.week===1?2:1)}] as Record<string,string>[])expect(()=>resolveEntry(i,new URLSearchParams(q))).toThrow();
    expect(()=>resolveEntry(i,new URLSearchParams(`game=${e.gameId}&game=${e.gameId}`))).toThrow();
    const base=new URLSearchParams('season=2026&week=1&q=Patriots&scope=season&filter=all&page=2'),href=matchupHref(base,e),back=calendarHref(new URLSearchParams(href.slice(2)),e.week);expect(back).toBe('/?season=2026&week=1&q=Patriots&scope=season&filter=all&page=2');
  });
  it('refuses incompatible packages, documents, participants, calendar and weeks',()=>{
    const e=index().games[0];const d=doc(e.gameId);d.game.home=d.game.away;expect(()=>validateDocument(d,e)).toThrow();
    const x=doc(e.gameId);x.calendar.homeScore=999;expect(()=>validateDocument(x,e)).toThrow();
    expect(()=>freezeW12({bundleId:'sha256:wrong',index:JSON.stringify(index()),documents:real!.documents})).toThrow();
    const wrong=index();wrong.games[0].week=2;expect(()=>validateIndex(wrong)).toThrow();
  });
  it('checks response bytes against index hash and collection markers',async()=>{
    const e=index().games[0],b=real!.documents[e.gameId];
    const ok=vi.fn().mockResolvedValue(new Response(b,{headers:{'X-Matchup-Collection':COLLECTION_PIN,'X-Matchup-Document':e.documentHash}}));expect((await loadDocument(e,undefined,ok)).game.gameId).toBe(e.gameId);
    const bad=vi.fn().mockResolvedValue(new Response('{}',{headers:{'X-Matchup-Collection':COLLECTION_PIN,'X-Matchup-Document':e.documentHash}}));await expect(loadDocument(e,undefined,bad)).rejects.toThrow('incompatíveis');expect(bad).toHaveBeenCalledTimes(1);
  });
});
