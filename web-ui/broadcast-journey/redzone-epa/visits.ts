import type {Campaign, Evidence} from '../w12/model';
import type {Reading, Unit} from './model';

export type Visit = {campaign:Campaign;initial:Evidence;plays:{unit:Unit;evidence:Evidence}[]};
export type VisitReading = {visits:Visit[];highlight:Visit['plays'][number]|null;ties:number};

// This is a join of the two original populations, never a new definition of a visit.
// Every EPA play must occur once in the campaign's observed red-zone evidence.
export function visitReading(reading:Reading,campaigns:Campaign[]):VisitReading {
 const ids=new Set<string>(),units=new Map(reading.units.map(u=>[u.id,u]));
 if(new Set(campaigns.map(c=>c.id)).size!==campaigns.length)throw new Error('Campanhas repetidas.');
 const visits=campaigns.map(c=>{
  if(!c.included||c.uncertain||!reading.gameIds.includes(c.gameId)||!c.entryEvidence.length)throw new Error('Campanha incompatível.');
  const entries=[...c.entryEvidence].sort((a,b)=>a.order_sequence-b.order_sequence);
  const plays=entries.flatMap(e=>{
   const id=`${e.game_id}:${e.play_id}`,u=units.get(id);
   if(!u)return [];
   if(ids.has(id)||u.gameId!==c.gameId||u.offense!==c.offense||u.defense!==c.defense||u.yardline!==e.yardline_100)throw new Error('Vínculo de jogada incompatível.');
   ids.add(id);return [{unit:u,evidence:e}];
  });
  return {campaign:c,initial:entries[0],plays};
 }).sort((a,b)=>a.campaign.week-b.campaign.week||a.campaign.gameId.localeCompare(b.campaign.gameId)||a.campaign.sourceOrder-b.campaign.sourceOrder);
 if(ids.size!==units.size)throw new Error('Há jogadas sem campanha demonstrada.');
 const valid=visits.flatMap(v=>v.plays).filter(p=>p.unit.epaStatus==='VALID'&&p.unit.epa!==null);
 // Decimal comparison preserves ties even when the source values differ below Float64 precision.
 const magnitude=(s:string)=>{const [mantissa,power='0']=s.replace(/^[+-]/,'').toLowerCase().split('e'),[a,b='']=mantissa.split('.'),exp=Number(power)-b.length,n=BigInt(a+b);return exp>=0?{n:n*10n**BigInt(exp),d:1n}:{n,d:10n**BigInt(-exp)};};
 const compare=(a:string,b:string)=>{const x=magnitude(a),y=magnitude(b);return x.n*y.d-y.n*x.d;};
 const highlight=valid.reduce<typeof valid[number]|null>((best,p)=>!best||compare(p.unit.epa!,best.unit.epa!)>0n?p:best,null);
 return {visits,highlight,ties:highlight?valid.filter(p=>compare(p.unit.epa!,highlight.unit.epa!)===0n).length:0};
}

export function situation(e:Evidence){
 const down=e.down==null?'Descida não informada':`${e.down}ª`,distance=e.ydstogo==null?'distância não informada':`${e.ydstogo} ${e.ydstogo===1?'jarda':'jardas'}`;
 return `${down} para ${distance} · a ${e.yardline_100} jardas da end zone`;
}
export function evidenceClock(e:Evidence){
 const q=e.qtr,s=e.game_seconds_remaining;
 if(q==null||s==null)return 'Relógio não informado';
 const r=q<=4?s-(4-q)*900:s;
 if(!Number.isInteger(r)||r<0||r>900)return 'Relógio não informado';
 return `${q===5?'Prorrogação':`${q}º quarto`} · ${String(Math.floor(r/60)).padStart(2,'0')}:${String(r%60).padStart(2,'0')}`;
}
