import {describe,it,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {loadRealFixture} from '../situational/real-fixture.mjs';
import {validateSnapshot} from '../situational/model';
import {activeSelection,comparison,encodePin,explorerHref,initialQuery,options,previousHref,project,resolvePins,type Question,type Slice} from './state';
import {SliceResult} from './Explorer';
import {SituationalContent} from '../situational/SituationalReading';
import type {Game} from '../../src/services/types';
const fixture=loadRealFixture();
const game={gameId:'2026_01_NYJ_TEN',season:2026,week:1,gameType:'REG',homeTeam:{teamAbbr:'TEN'},awayTeam:{teamAbbr:'NYJ'}} as Game;
const game2={...game,gameId:'2026_02_GB_NYJ',week:2,homeTeam:{teamAbbr:'NYJ'},awayTeam:{teamAbbr:'GB'}} as Game;
const base=()=>new URLSearchParams({view:'explorer',game:game.gameId,team:'NYJ',side:'off',reading:'game',analysis:'third',question:'distance',refine:'long',week:'1',q:'jets'});
describe('explorer URL contract',()=>{
 it('opens a labelled example only without explicit context and preserves invalid explicit values',()=>{
  const n=initialQuery(new URLSearchParams('view=explorer'),[game]);expect(n.get('example')).toBe('nyj');expect(n.get('game')).toBe(game.gameId);
  for(const key of ['game','team','side','reading']){const q=base();q.set(key,'invalid');expect(initialQuery(q,[game]).get(key)).toBe('invalid');}
  const q=base();expect(initialQuery(q,[game]).toString()).toBe(q.toString());
 });
 it('keeps origin and context through explicit entry, return and summary links',()=>{
  const q=base();for(const link of [explorerHref(q),previousHref(q),previousHref(q,true)]){const n=new URLSearchParams(link.slice(2));for(const key of ['game','team','side','reading','week','q'])expect(n.get(key)).toBe(q.get(key));}
  expect(previousHref(q,true)).toContain('analysis=summary');
 });
});
describe.skipIf(!fixture)('explorer real source projections (operator configured)',()=>{
 const s=fixture?validateSnapshot({transportVersion:'situational-response-v1',bundleId:fixture.bundleId,data:fixture.data}):null;
 function source(){if(!s)throw Error('No operator source');return s;}
 const pin=(document='NYJ/off/1',question:Question='distance',refine='long'):Slice=>({document,question,refine,bundle:source().bundleId});
 it('matches every numerator, denominator, status and source document across all supported projections without mutation',()=>{
  const snapshot=source(),before=JSON.stringify(snapshot);
  for(const d of snapshot.data.documents)for(const question of ['distance','type','outcomes'] as const)for(const refine of Object.keys(options(question))){
   const v=project(d,question,refine),m=question==='outcomes'?d.redZone:d.third;
   const expected=question==='outcomes'?{numerator:refine==='all'?m.numerator:d.redZone.outcomes[refine]??0,denominator:m.denominator}:refine==='all'?m:question==='distance'?d.third.byDistance[refine]:d.third.byType[refine];
   expect(v.numerator).toBe(expected.numerator);expect(v.denominator).toBe(expected.denominator);expect(v.status).toBe(m.status);
   if(m.status!=='AVAILABLE'||!v.denominator)expect(v.rate).toBeNull();
   const html=renderToStaticMarkup(<SliceResult d={d} question={question} refine={refine} onRefine={()=>{}}/>);expect(html).toContain(`data-document="${d.id}"`);expect(html).toContain(`${v.numerator} / ${v.denominator}`);
  }
  expect(JSON.stringify(snapshot)).toBe(before);
 });
 it('selects NYJ long thirds 1/5, retains W1 and side when changing family, and refuses a joint marginal',()=>{
  const snapshot=source(),q=base();expect(project(activeSelection(snapshot,game,q).document!,'distance','long')).toMatchObject({numerator:1,denominator:5});
  q.set('question','outcomes');q.set('analysis','redzone');q.set('refine','all');expect(activeSelection(snapshot,game,q).document!.id).toBe('NYJ/off/1');expect(project(activeSelection(snapshot,game,q).document!,'outcomes','all')).toMatchObject({numerator:2,denominator:3});
  q.set('side','def');expect(activeSelection(snapshot,game,q).document!.id).toBe('NYJ/def/1');
  q.set('refine','long_run');expect(activeSelection(snapshot,game,q).error).toBeTruthy();
 });
 it('preserves the campaign denominator for a highlighted outcome',()=>{
  const d=source().data.documents.find(d=>d.id==='NYJ/off/1')!;expect(project(d,'outcomes','FIELD_GOAL')).toMatchObject({numerator:1,denominator:3,rate:{numerator:1,denominator:3}});
  const html=renderToStaticMarkup(<SliceResult d={d} question="outcomes" refine="FIELD_GOAL" onRefine={()=>{}}/>);expect(html).toContain('Taxa de TD do documento: 2/3');expect(html).not.toContain('100,0%');
 });
 it('reconstructs pinned source identities from URL after active W2 changes, including two slots',()=>{
  const q=base(),p=pin();q.append('pin',encodePin(p));const encoded=q.toString();q.set('game',game2.gameId);q.set('side','def');q.set('question','type');q.set('refine','run');
  expect(resolvePins(new URLSearchParams(q.toString()),source()).slices).toEqual([p]);expect(resolvePins(new URLSearchParams(encoded),source()).slices).toEqual([p]);
  q.append('pin',encodePin(pin('NYJ/off/2')));expect(resolvePins(q,source()).slices).toHaveLength(2);q.append('pin',encodePin(pin('NYJ/off/1-2')));expect(resolvePins(q,source()).error).toBeTruthy();
 });
 it('rejects untrusted counts, wrong bundle, wrong document, duplicate or malformed pins',()=>{
  for(const raw of ['1/5',encodePin({...pin(),bundle:'another'}),encodePin({...pin(),document:'missing'}),encodePin({...pin(),refine:'long_run'}),encodePin({...pin(),question:'constructor' as Question})]){const q=base();q.set('pin',raw);expect(resolvePins(q,source()).error).toBeTruthy();}
  const q=base();q.append('pin',encodePin(pin()));q.append('pin',encodePin(pin()));expect(resolvePins(q,source()).error).toBeTruthy();
 });
 it('labels overlapping periods and incompatible families or numerator meanings without differences',()=>{
  const snapshot=source();expect(comparison(pin(),pin('NYJ/off/2'),snapshot)).toEqual({compatible:true,overlap:false});expect(comparison(pin(),pin('NYJ/off/1-2'),snapshot)).toEqual({compatible:true,overlap:true});expect(comparison(pin(),pin('NYJ/off/1','outcomes','all'),snapshot).compatible).toBe(false);expect(comparison(pin(),pin('NYJ/off/1','distance','short'),snapshot).compatible).toBe(false);
 });
 it('keeps zero opportunities, insufficient evidence and absent source distinct',()=>{
  const snapshot=source(),d=snapshot.data.documents.find(d=>d.id==='ATL/off/1')!;
  expect(project(d,'outcomes','all').rate).toBeNull();const zero=renderToStaticMarkup(<SliceResult d={d} question="outcomes" refine="all" onRefine={()=>{}}/>);expect(zero).toContain('Fonte presente, sem oportunidades');expect(zero).not.toContain('0,0%');
  const insufficient=structuredClone(snapshot.data.documents[0]);Object.assign(insufficient.third,{status:'INSUFFICIENT',ratio:null,ambiguousIds:['synthetic-test-only']});expect(project(insufficient,'distance','long').rate).toBeNull();expect(renderToStaticMarkup(<SliceResult d={insufficient} question="distance" refine="long" onRefine={()=>{}}/>)).toContain('insuficientes ou contraditórias');
  expect(activeSelection(snapshot,{...game,week:3},base()).absent).toBe(true);
 });
 it('rejects invalid investigation URL dimensions, including prototype property names',()=>{
  for(const [k,v] of [['team','BAD'],['side','bad'],['reading','bad'],['question','constructor'],['question','__proto__'],['refine','constructor'],['analysis','bad'],['entry','old']]){const q=base();q.set(k,v);expect(activeSelection(source(),game,q).error).toBeTruthy();}
 });
 it('uses one active announcement while the original reading keeps its default',()=>{
  const snapshot=source(),d=snapshot.data.documents[0];
  const original=renderToStaticMarkup(<SituationalContent d={d} snapshot={snapshot} family="third"/>),quiet=renderToStaticMarkup(<SituationalContent d={d} snapshot={snapshot} family="third" announce={false}/>);
  expect(original).toContain('aria-live="polite"');expect(quiet).toBe(original.replace('aria-live="polite"','aria-live="off"'));
 });
 it('requires original game membership and opponent consistency',()=>{
  expect(activeSelection(source(),{...game,homeTeam:{teamAbbr:'BAD'}} as Game,base()).error).toBeTruthy();
 });
});
