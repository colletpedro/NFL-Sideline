import {describe,it,expect} from 'vitest';
import {renderToStaticMarkup} from 'react-dom/server';
import {fixture} from '../season/fixture.mjs';
import {visitReading,evidenceClock,situation} from './visits';
import {VisitNarrative} from './VisitNarrative';
import type {Reading} from './model';
import type {Campaign} from '../w12/model';

const f=fixture();
describe.skipIf(!f)('visits from the original W1–7 campaigns',()=>{
 it('assigns every eligible EPA play exactly once without splitting campaigns or changing means',()=>{
  let visits=0,plays=0;
  for(const d of Object.values(f!.games))for(const [i,r] of d.redzoneEpa.productions.entries()){
   const before=JSON.stringify(r),v=visitReading(r,d.productions[i].redZoneCampaigns);
   expect(v.visits).toHaveLength(d.productions[i].metrics.redZone.descriptor.denominator!);
   expect(v.visits.flatMap(v=>v.plays.map(p=>p.unit.id)).sort()).toEqual(r.units.map(u=>u.id).sort());
   expect(JSON.stringify(r)).toBe(before);visits+=v.visits.length;plays+=r.units.length;
  }
  expect(visits).toBe(723);expect(plays).toBe(2096);
 });
 it('keeps season offense and opponent populations complete, with game-specific campaign IDs',()=>{
  for(const d of Object.values(f!.teams))for(const [i,r] of d.redzoneEpa.productions.entries()){
   const v=visitReading(r,d.productions[i].redZoneCampaigns);
   expect(v.visits.flatMap(v=>v.plays)).toHaveLength(r.units.length);
   expect(v.visits).toHaveLength(d.productions[i].metrics.redZone.descriptor.denominator!);
  }
 });
 it('reveals BAL play 2836 with its actual fourth-down, distance, clock and description',()=>{
  const d=f!.games['2026_07_CIN_BAL'],r=d.redzoneEpa.productions[1],c=d.productions[1].redZoneCampaigns,v=visitReading(r,c);
  expect(v.visits).toHaveLength(3);expect(v.highlight?.unit.playId).toBe(2836);
  expect(v.highlight?.unit.epa).toBe('-3.114080941246357');
  expect(evidenceClock(v.highlight!.evidence)).toBe('4º quarto · 15:00');
  expect(situation(v.highlight!.evidence)).toBe('4ª para 2 jardas · a 12 jardas da end zone');
  const html=renderToStaticMarkup(<VisitNarrative rows={[{label:'BAL com a bola',reading:r}]} campaigns={[c]}/>);
  expect(html).toContain('pass incomplete short middle');expect(html).toContain('−3,114');expect(html).not.toContain('<details open');
 });
 it('refuses unmatched, duplicate and incompatible play-to-campaign evidence instead of silently dropping plays',()=>{
  const d=f!.games['2026_07_CIN_BAL'],r=d.redzoneEpa.productions[1],c=d.productions[1].redZoneCampaigns;
  expect(()=>visitReading(r,c.slice(1))).toThrow();expect(()=>visitReading(r,[...c,c[0]])).toThrow();
  const broken=structuredClone(c);broken[0].entryEvidence[0].yardline_100=99;
  expect(()=>visitReading(r,broken)).toThrow();
 });
 it('keeps zero opportunities and a real zero EPA distinct, with no fabricated situation',()=>{
  const d=f!.games['2026_01_ATL_PIT'],r=d.redzoneEpa.productions[0];
  expect(visitReading(r,[]).highlight).toBeNull();
  const game=f!.games['2026_07_CIN_BAL'],row=structuredClone(game.redzoneEpa.productions[1]) as Reading;
  row.units.forEach(u=>{u.epa='0';u.epaStatus='VALID';});
  const v=visitReading(row,game.productions[1].redZoneCampaigns as Campaign[]);
  expect(v.highlight?.unit.epa).toBe('0');expect(v.ties).toBe(row.validN);
  const e={game_id:'x',play_id:1,desc:'',yardline_100:10,order_sequence:1};
  expect(evidenceClock(e)).toBe('Relógio não informado');expect(situation(e)).toContain('Descida não informada');
 });
});
