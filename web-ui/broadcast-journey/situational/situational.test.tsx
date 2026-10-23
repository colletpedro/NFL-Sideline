import { describe,expect,it } from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {percent,selectDocument,validateSnapshot,type Snapshot,type SituationalDocument} from './model';
import {SituationalContent} from './SituationalReading';
import {allowedSituationalRequest} from '../../build/situational';
const hash='sha256:'+'a'.repeat(64);
function synthetic():Snapshot {
  const documents:SituationalDocument[]=[];
  const m={numerator:1,denominator:3,status:'AVAILABLE' as const,denominatorState:'POSITIVE' as const,ratio:{numerator:1,denominator:3},unitIds:['a','b','c'],excludedIds:['d'],exclusions:{NO_PLAY:1},ambiguousIds:[]};
  for(let i=0;i<32;i++)for(const side of ['off','def'] as const)for(const weeks of [[1],[2],[1,2]]) {
    const team='A'+String.fromCharCode(65+Math.floor(i/26))+String.fromCharCode(65+i%26);
    documents.push({id:`${team}/${side}/${weeks.join('-')}`,team,perspective:side,season:2026,phase:'REG',weeks,
      games:weeks.map(week=>({gameId:`SYNTHETIC_${week}_${team}`,week,home:team,away:'ZZZ',opponent:'ZZZ'})),
      third:{...structuredClone(m),byType:{pass:{numerator:1,denominator:2},run:{numerator:0,denominator:1}},byDistance:{short:{numerator:1,denominator:1},medium:{numerator:0,denominator:1},long:{numerator:0,denominator:1},unknown:{numerator:0,denominator:0}},penaltyFirstDowns:{included:0,excluded:1},sacks:1,scrambles:1},
      redZone:{...structuredClone(m),exclusions:{NO_ENTRY:1},outcomes:{TOUCHDOWN:1,FIELD_GOAL:2},observedEntries:3}});
  }
  return {transportVersion:'situational-response-v1',bundleId:hash,data:{contractVersion:'situational-v1',definitionsVersion:'1.0.0',calculationVersion:'1.0.0',ledgerHash:hash,provenance:{rawHash:hash,materializationId:hash,inputId:hash},guarantees:{completeness:'UNKNOWN',expectedCoverage:'UNKNOWN',epaModel:'UNKNOWN',temporalKnowledge:'UNKNOWN'},documents}};
}
const game={gameId:'SYNTHETIC_1_AAA',season:2026,week:1,homeTeam:{teamAbbr:'AAA'},awayTeam:{teamAbbr:'ZZZ'}};
describe('situational-v1 synthetic contract and route tests',()=>{
  it('validates the explicit contract and rejects altered counts, ratios, populations and versions',()=>{
    expect(validateSnapshot(synthetic()).data.documents).toHaveLength(192);
    for(const mutate of [(s:Snapshot)=>s.data.documents[0].third.denominator++, (s:Snapshot)=>s.data.documents[0].third.ratio!.numerator++, (s:Snapshot)=>s.data.documents[0].redZone.outcomes.TOUCHDOWN++, (s:Snapshot)=>s.data.documents[0].third.unitIds.push('a'), (s:Snapshot)=>s.data.definitionsVersion='unknown', (s:Snapshot)=>s.data.documents.pop()]) {
      const s=synthetic();mutate(s);expect(()=>validateSnapshot(s)).toThrow();
    }
  });
  it('keeps exact integer rounding, including half-up and zero denominator',()=>{
    expect(percent({numerator:1,denominator:3})).toBe('33,3%');expect(percent({numerator:1,denominator:16})).toBe('6,3%');expect(percent({numerator:0,denominator:4})).toBe('0,0%');expect(percent({numerator:0,denominator:0})).toBeNull();expect(percent(null)).toBeNull();
  });
  it('retains team, perspective and inclusive period under rapid selections without stale requests',()=>{
    const s=synthetic();
    for(let i=0;i<50;i++){
      const side=i%2?'off':'def',period=i%3?'game':'2026/REG/1,2';const q=new URLSearchParams({team:'AAA',side,reading:period,analysis:i%2?'third':'redzone',q:'busca preservada'});
      const d=selectDocument(s,game,q,'AAA').document!;
      expect(d.id).toBe(`AAA/${side}/${period==='game'?'1':'1-2'}`);expect(q.get('q')).toBe('busca preservada');
    }
  });
  it('rejects invalid dimensions and nominal legacy identities without fallback',()=>{
    for(const change of [['team','NO'],['side','wrong'],['reading','2026/REG/2'],['entry','old'],['observation','missing']]) expect(selectDocument(synthetic(),game,new URLSearchParams([change]),'AAA').error).toBeTruthy();
  });
  it('rejects a calendar opponent contradiction for an otherwise matching game ID',()=>{
    expect(selectDocument(synthetic(),{...game,awayTeam:{teamAbbr:'BAD'}},new URLSearchParams(),'AAA').error).toBeTruthy();
    expect(selectDocument(synthetic(),{...game,gameType:'POST'},new URLSearchParams(),'AAA').absent).toBe(true);
  });
  it('distinguishes source absence in W3 from present/zero opportunities',()=>{
    expect(selectDocument(synthetic(),{...game,week:3},new URLSearchParams(),'AAA').absent).toBe(true);
    const s=synthetic(),d=s.data.documents[0];Object.assign(d.redZone,{numerator:0,denominator:0,status:'NO_OPPORTUNITIES',denominatorState:'ZERO',ratio:null,unitIds:[],outcomes:{},observedEntries:0});
    const html=renderToStaticMarkup(<SituationalContent d={d} snapshot={s} family="redzone"/>);expect(html).toContain('Denominador zero');expect(html).not.toContain('0,0%');expect(html).not.toContain('sit-drive-marks');
  });
  it('renders factual ratios, defense attribution and distinct accessible charts',()=>{
    const s=synthetic(),d=s.data.documents.find(x=>x.perspective==='def')!;
    const third=renderToStaticMarkup(<SituationalContent d={d} snapshot={s} family="third"/>),rz=renderToStaticMarkup(<SituationalContent d={d} snapshot={s} family="redzone"/>);
    for(const html of [third,rz]){expect(html).toContain('33,3%');expect(html).toContain('1 / 3');expect(html).toContain('permitido ao ataque adversário');expect(html).toContain('role="img"');expect(html).toContain('Semana 1');}
    expect(third).toContain('sit-distance');expect(third).not.toContain('sit-drive-marks');expect(rz).toContain('sit-drive-marks');expect(rz).not.toContain('sit-distance');
  });
  it('restricts transport to marked GET with exact loopback host and path',()=>{
    const h={host:'127.0.0.1:18098','x-local-situational':'1'};
    expect(allowedSituationalRequest('GET','/__situational/',h,18098)).toBe(true);
    for(const [method,url,headers] of [['POST','/__situational/',h],['GET','/__situational/?path=/tmp',h],['GET','/__situational/',{...h,origin:'https://example.com'}],['GET','/__situational/',{...h,'content-length':'1'}],['GET','/__situational/',{...h,host:'localhost:18098'}],['GET','/__situational/',{host:h.host}]] as const) expect(allowedSituationalRequest(method,url,headers,18098)).toBe(false);
  });
});
