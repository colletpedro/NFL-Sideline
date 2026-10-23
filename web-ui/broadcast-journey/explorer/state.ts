import type { Game } from '../../src/services/types';
import { selectDocument, type Fraction, type Snapshot, type SituationalDocument } from '../situational/model';
export const questions = { distance: 'Conversões de terceira por distância', type: 'Passe e corrida nas terceiras descidas', outcomes: 'Desfechos das campanhas de red zone' };
export type Question = keyof typeof questions;
export type Slice = { document: string; question: Question; refine: string; bundle: string };
export const distances = { all: 'Todas as distâncias', short: 'Curtas · 1–3 jardas', medium: 'Médias · 4–6 jardas', long: 'Longas · 7+ jardas', unknown: 'Distância não informada' };
export const types = { all: 'Passe e corrida', pass: 'Passe · inclui sacks', run: 'Corrida · inclui scrambles' };
export const outcomes: Record<string,string> = { all: 'Todos os desfechos', TOUCHDOWN: 'Touchdown ofensivo', FIELD_GOAL: 'Field goal', MISSED_FIELD_GOAL: 'Field goal perdido/bloqueado', TURNOVER: 'Turnover', OPPONENT_TOUCHDOWN: 'Touchdown do time que defendia', DOWNS: 'Perda por descidas', PUNT: 'Punt', END_HALF_GAME: 'Fim de tempo/jogo', SAFETY: 'Safety' };
export function options(question: Question): Record<string,string> { return question === 'distance' ? distances : question === 'type' ? types : outcomes; }
export function family(question: Question) { return question === 'outcomes' ? 'redzone' : 'third'; }
export function explorerHref(q: URLSearchParams) {
  const n = new URLSearchParams(q); n.set('view','explorer'); n.delete('entry'); n.delete('observation');
  const question = n.get('analysis') === 'redzone' ? 'outcomes' : n.get('question') === 'type' ? 'type' : 'distance';
  n.set('question',question); n.set('analysis',family(question));
  if (!Object.prototype.hasOwnProperty.call(options(question),n.get('refine') ?? 'all')) n.delete('refine');
  return `/?${n}`;
}
export function previousHref(q: URLSearchParams, summary = false) {
  const n = new URLSearchParams(q); n.delete('view');
  if (summary) n.set('analysis','summary');
  return `/?${n}`;
}
// A URL with explicit, invalid context never receives a substitute document.
export function initialQuery(q: URLSearchParams, games: Game[]) {
  const n = new URLSearchParams(q), named = q.has('game');
  const team = q.get('team') ?? (named ? games.find(g=>g.gameId===q.get('game'))?.awayTeam.teamAbbr : 'NYJ');
  const game = named ? games.find(g=>g.gameId===q.get('game')) : games.find(g=>g.season===Number(q.get('season')??2026) && g.week===Number(q.get('week')??1) && [g.homeTeam.teamAbbr,g.awayTeam.teamAbbr].includes(team??''));
  if (!game || !team) return n;
  const example = !['game','team','side','reading','entry','observation'].some(k=>q.has(k));
  for (const [k,v] of Object.entries({game:game.gameId,team,side:'off',reading:'game',question:q.get('analysis')==='redzone'?'outcomes':'distance'})) if (!n.has(k)) n.set(k,v);
  if (!n.has('analysis') || n.get('analysis')==='summary') n.set('analysis',family(n.get('question') as Question));
  if (example) n.set('example','nyj');
  return n;
}
export function activeSelection(s: Snapshot, game: Game, q: URLSearchParams) {
  const question = q.get('question') ?? 'distance', refine = q.get('refine') ?? 'all';
  if (!Object.prototype.hasOwnProperty.call(questions,question) || !Object.prototype.hasOwnProperty.call(options(question as Question),refine) || q.get('analysis') !== family(question as Question)) return { error: 'Pergunta ou refinamento inválido na URL. Escolha uma pergunta para continuar.' };
  return selectDocument(s,game,q,q.get('team')??game.awayTeam.teamAbbr);
}
export type Projection = Fraction & { unit: 'tentativas'|'campanhas'; label:string; rate:Fraction|null; status:string };
// Presentation projection only. Never rewrite the document or pretend marginals are joint data.
export function project(d: SituationalDocument, question: Question, refine: string): Projection {
  const m = question==='outcomes' ? d.redZone : d.third;
  const f = question==='outcomes' ? {numerator:refine==='all'?m.numerator:d.redZone.outcomes[refine]??0,denominator:m.denominator} : refine==='all' ? m : question==='distance' ? d.third.byDistance[refine] : d.third.byType[refine];
  return {...f, unit:question==='outcomes'?'campanhas':'tentativas', label:refine==='all'?(question==='outcomes'?'Touchdowns ofensivos':'Conversões'):question==='outcomes'?options(question)[refine]:`Conversões · ${options(question)[refine]}`,rate:m.status==='AVAILABLE' && f.denominator>0?{numerator:f.numerator,denominator:f.denominator}:null,status:m.status};
}
export function encodePin(slice: Slice) { return [slice.document,slice.question,slice.refine,slice.bundle].join('~'); }
export function resolvePins(q: URLSearchParams, snapshot: Snapshot): {slices:Slice[];error?:string} {
  const pins=q.getAll('pin'); const slices:Slice[]=[];
  if(pins.length>2) return {slices,error:'A URL contém mais de dois recortes fixados. Remova-os para reconstruir a comparação.'};
  for(const pin of pins) {
    const [document,question,refine,bundle,...extra]=pin.split('~');
    if(extra.length || !Object.prototype.hasOwnProperty.call(questions,question) || !Object.prototype.hasOwnProperty.call(options(question as Question),refine) || bundle!==snapshot.bundleId || !snapshot.data.documents.some(d=>d.id===document)) return {slices:[],error:'Recorte fixado inválido ou fonte diferente da sessão. Nenhum número da URL foi usado.'};
    slices.push({document,question:question as Question,refine,bundle});
  }
  if(new Set(pins).size!==pins.length)return {slices:[],error:'A URL repete o mesmo recorte fixado.'};
  return {slices};
}
export function comparison(a: Slice,b: Slice,s:Snapshot) {
  const da=s.data.documents.find(d=>d.id===a.document)!,db=s.data.documents.find(d=>d.id===b.document)!;
  const compatible=family(a.question)===family(b.question) && a.question===b.question && a.refine===b.refine;
  const overlap=da.games.some(g=>db.games.some(h=>h.gameId===g.gameId));
  return {compatible,overlap};
}
