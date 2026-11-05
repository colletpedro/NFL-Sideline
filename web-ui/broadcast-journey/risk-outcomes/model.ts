export const OUTCOME_ENDPOINT='/__risk-outcomes/';
export const B2_SHA='ebc588e7990e29fb2e5ba8848558c1e5948222d7a6f002f07575a66d38186db8';
export const B2_ID='XINT-FTN-B2-v1-fit2025';
export type OutcomeCounts={eligiblePasses:number;games:number;interceptionWorthyPasses:number;observedInterceptions:number;expectedInterceptions:number;expectedFromClassified:number;expectedFromNotClassified:number;differenceInterceptions:number;differencePer100:number|null};
export type OutcomeGame=OutcomeCounts&{gameId:string;week:number;home:string;away:string;date:string};
export type OutcomePlayer=OutcomeCounts&{id:string;name:string;teams:string[];positionClass:'qb'|'other'|'unknown';positions:string[];byGame:OutcomeGame[]};
export type OutcomePlay={id:string;gameId:string;playId:number;week:number;date:string;team:string;opponent:string;passerId:string;name:string;position:string|null;positionClass:string;quarter:number;clock:string;down:number;distance:number;fieldPosition:number;scoreDifferential:number;ftnInterceptionWorthy:boolean;observedInterception:boolean;pInterceptionGivenFtn:number;description:string|null;evidence:{source:string;gameId:string;playId:number}};
type GameMeta={gameId:string;week:number;home:string;away:string;date:string;passes:number};
export type OutcomeIndex={schemaVersion:1;presentationVersion:'1.0.0';target:'observed_interception';packageId:string;season:2026;phase:'REG';acquiredAt:string;checkedAt?:string;model:{id:string;sha256:string;referenceSeason:number;rateClassified:number;rateNotClassified:number;referenceClassified:{events:number;passes:number};referenceNotClassified:{events:number;passes:number}};scientific:{consumerIndexSha256:string;integritySha256:string;sourceManifestSha256:string};coverage:{games:number;completedGames:number;scheduledGames:number;weeks:number[];pendingGames:(GameMeta&{reason:string})[];scheduled:(GameMeta&{reason:string})[];included:GameMeta[];pbpWeeks:number[];ftnWeeks:number[]};summary:OutcomeCounts;players:OutcomePlayer[];comparison:{m3PackageId:string;sameEligiblePasses:boolean;sharedPasses:number;onlyM3:number;onlyB2:number;revisedPasses:number};attribution:string;interpretation:string};
export type OutcomeDetail={packageId:string;player:OutcomePlayer;plays:OutcomePlay[]};
function check(v:unknown,message='Pacote de interceptações incompatível. Nenhum valor substituto foi usado.'):asserts v{if(!v)throw new Error(message);}
const near=(a:number,b:number)=>Number.isFinite(a)&&Math.abs(a-b)<1e-8;
export function assertOutcomeCounts(c:OutcomeCounts){
 check(c&&Number.isSafeInteger(c.eligiblePasses)&&c.eligiblePasses>=0&&Number.isSafeInteger(c.games)&&c.games>=0&&c.games<=c.eligiblePasses);
 for(const v of [c.observedInterceptions,c.interceptionWorthyPasses])check(Number.isSafeInteger(v)&&v>=0&&v<=c.eligiblePasses);
 check(Number.isFinite(c.expectedInterceptions)&&c.expectedInterceptions>=0&&c.expectedInterceptions<=c.eligiblePasses&&c.expectedFromClassified>=0&&c.expectedFromNotClassified>=0&&near(c.expectedInterceptions,c.expectedFromClassified+c.expectedFromNotClassified)&&near(c.differenceInterceptions,c.observedInterceptions-c.expectedInterceptions));
 check(c.eligiblePasses===0?c.differencePer100===null:typeof c.differencePer100==='number'&&near(c.differencePer100,100*c.differenceInterceptions/c.eligiblePasses));
}
export function outcomeCounts(plays:OutcomePlay[]):OutcomeCounts{
 const eligiblePasses=plays.length,observedInterceptions=plays.filter(p=>p.observedInterception).length,interceptionWorthyPasses=plays.filter(p=>p.ftnInterceptionWorthy).length,expectedFromClassified=plays.filter(p=>p.ftnInterceptionWorthy).reduce((s,p)=>s+p.pInterceptionGivenFtn,0),expectedFromNotClassified=plays.filter(p=>!p.ftnInterceptionWorthy).reduce((s,p)=>s+p.pInterceptionGivenFtn,0),expectedInterceptions=expectedFromClassified+expectedFromNotClassified,differenceInterceptions=observedInterceptions-expectedInterceptions;
 return {eligiblePasses,games:new Set(plays.map(p=>p.gameId)).size,observedInterceptions,interceptionWorthyPasses,expectedInterceptions,expectedFromClassified,expectedFromNotClassified,differenceInterceptions,differencePer100:eligiblePasses?100*differenceInterceptions/eligiblePasses:null};
}
const countFields=['eligiblePasses','games','observedInterceptions','interceptionWorthyPasses','expectedInterceptions','expectedFromClassified','expectedFromNotClassified','differenceInterceptions'] as const;
export function validateOutcomeIndex(v:unknown):OutcomeIndex{
 const i=v as OutcomeIndex;check(i?.schemaVersion===1&&i.presentationVersion==='1.0.0'&&i.target==='observed_interception'&&i.season===2026&&i.phase==='REG'&&/^[a-f0-9]{24}$/.test(i.packageId)&&i.model?.id===B2_ID&&i.model.sha256===B2_SHA&&i.model.referenceSeason===2025&&Array.isArray(i.players));
 for(const [rate,support] of [[i.model.rateClassified,i.model.referenceClassified],[i.model.rateNotClassified,i.model.referenceNotClassified]] as const)check(rate>0&&rate<1&&support.passes>0&&near(rate,support.events/support.passes));
 check(Number.isFinite(Date.parse(i.acquiredAt))&&new Set(i.players.map(p=>p.id)).size===i.players.length);assertOutcomeCounts(i.summary);
 for(const p of i.players){check(/^00-\d{7}$/.test(p.id)&&p.name&&['qb','other','unknown'].includes(p.positionClass)&&p.teams.length>0);assertOutcomeCounts(p);check(p.byGame.length===p.games&&new Set(p.byGame.map(g=>g.gameId)).size===p.byGame.length);for(const g of p.byGame){assertOutcomeCounts(g);check(i.coverage.included.some(c=>c.gameId===g.gameId&&c.week===g.week));}for(const key of countFields.filter(k=>k!=='games'))check(near(p[key],p.byGame.reduce((s,g)=>s+g[key],0)));}
 check(i.summary.games===i.coverage.games&&i.coverage.games===i.coverage.included.length&&i.coverage.completedGames===i.coverage.games+i.coverage.pendingGames.length&&new Set(i.coverage.weeks).size===i.coverage.weeks.length);
 for(const key of ['eligiblePasses','observedInterceptions','interceptionWorthyPasses','expectedInterceptions','expectedFromClassified','expectedFromNotClassified'] as const)check(near(i.summary[key],i.players.reduce((s,p)=>s+p[key],0)));
 return i;
}
export function validateOutcomeDetail(v:unknown,i:OutcomeIndex,id:string):OutcomeDetail{
 const d=v as OutcomeDetail;check(d?.packageId===i.packageId&&d.player?.id===id&&Array.isArray(d.plays));check(new Set(d.plays.map(p=>p.id)).size===d.plays.length);
 for(const p of d.plays)check(p.passerId===id&&typeof p.ftnInterceptionWorthy==='boolean'&&typeof p.observedInterception==='boolean'&&p.id===`${p.gameId}:${p.playId}`&&near(p.pInterceptionGivenFtn,p.ftnInterceptionWorthy?i.model.rateClassified:i.model.rateNotClassified)&&p.pInterceptionGivenFtn>0&&p.pInterceptionGivenFtn<1&&i.coverage.included.some(g=>g.gameId===p.gameId&&g.week===p.week));
 const c=outcomeCounts(d.plays),s=i.players.find(p=>p.id===id);check(s);for(const key of countFields)check(near(c[key],s[key])&&near(c[key],d.player[key]));return d;
}
export function outcomePeriod(p:OutcomePlayer,period:string):OutcomePlayer{
 if(period==='all')return p;const byGame=p.byGame.filter(g=>g.week===Number(period));
 const eligiblePasses=byGame.reduce((s,g)=>s+g.eligiblePasses,0),observedInterceptions=byGame.reduce((s,g)=>s+g.observedInterceptions,0),interceptionWorthyPasses=byGame.reduce((s,g)=>s+g.interceptionWorthyPasses,0),expectedFromClassified=byGame.reduce((s,g)=>s+g.expectedFromClassified,0),expectedFromNotClassified=byGame.reduce((s,g)=>s+g.expectedFromNotClassified,0),expectedInterceptions=expectedFromClassified+expectedFromNotClassified,differenceInterceptions=observedInterceptions-expectedInterceptions;
 return {...p,byGame,eligiblePasses,games:byGame.length,observedInterceptions,interceptionWorthyPasses,expectedFromClassified,expectedFromNotClassified,expectedInterceptions,differenceInterceptions,differencePer100:eligiblePasses?100*differenceInterceptions/eligiblePasses:null};
}
export function outcomeRoute(q:URLSearchParams){
 const keys=['view','reading','season','period','player','cross','sort','volume','position','search','play','game','page','scale','group'];for(const k of q.keys())check(keys.includes(k)&&q.getAll(k).length===1,'Parâmetro de URL inválido ou repetido.');
 check(q.get('view')==='risk-lab'&&q.get('reading')==='interceptions'&&(!q.has('season')||q.get('season')==='2026'));
 const period=q.get('period')??'all',scale=q.get('scale')??'total',position=q.get('position')??'qb',player=q.get('player'),cross=q.get('cross')??'all',page=Number(q.get('page')??1);
 check(period==='all'||/^(?:[1-9]|1[0-8])$/.test(period));check(['total','per100'].includes(scale)&&['qb','other','unknown','all'].includes(position)&&['all','11','10','01','00'].includes(cross)&&Number.isInteger(page)&&page>=1&&page<=1000);
 if(player)check(/^00-\d{7}$/.test(player));if(q.has('play'))check(player,'Escolha um lançador para consultar a jogada.');return {period,scale:scale as 'total'|'per100',position,player,cross,page,play:q.get('play'),game:q.get('game')};
}
export async function requestOutcome(path:string,signal:AbortSignal){try{const r=await fetch(OUTCOME_ENDPOINT+path,{signal,headers:{'X-Risk-Lab':'1'}});if(!r.ok)throw new Error();return await r.json() as unknown;}catch(e){if(signal.aborted)throw e;throw new Error('Os dados de interceptações não puderam ser carregados. Tente novamente.');}}
