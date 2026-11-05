import type {Counts,Player} from './model';
export const metricLabels={classified:'Passes classificados como interceptáveis',expected:'Passes interceptáveis esperados',interceptions:'Interceptações sofridas'};
export type Scale='total'|'per100';
export const number=(x:number,d=1)=>(Math.abs(x)<.5*10**-d?0:x).toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d});
export const signed=(x:number,d=1)=>(x>=.5*10**-d?'+':'')+number(x,d);
export function shortName(name:string){const parts=name.split(' ');return parts.length===1?name:parts[0][0]+'. '+parts.slice(1).join(' ');}
export function coordinates(p:Counts,scale:Scale){if(p.passes===0)return null;const denominator=scale==='per100'?p.passes/100:1;return {x:p.expected/denominator,y:p.observed/denominator};}
export function domainFor(players:Player[],scale:Scale){const max=Math.max(0,...players.flatMap(p=>{const c=coordinates(p,scale);return c?[c.x,c.y]:[];}));if(!max)return {max:1,step:.2};const raw=max*1.08/5,power=10**Math.floor(Math.log10(raw)),step=[1,2,5,10].map(v=>v*power).find(v=>v>=raw)!;return {max:Math.ceil(max*1.08/step)*step,step};}
export type Point={player:Player;x:number;y:number;px:number;py:number};
// Shared numeric domain, independent x/y projection: equality need not look like 45 degrees.
export function scatterLayout(players:Player[],scale:Scale,width:number,fontScale=1){
 const bounds={left:42*fontScale,top:24,width:Math.max(120,width-42*fontScale-24),height:Math.max(260,Math.min(440,width*.43))},domain=domainFor(players,scale);
 const points=players.flatMap(player=>{const c=coordinates(player,scale);return c?[{player,...c,px:bounds.left+c.x/domain.max*bounds.width,py:bounds.top+bounds.height-c.y/domain.max*bounds.height}]:[];});
 return {bounds,domain,points,height:bounds.top+bounds.height+32*fontScale};
}
export function nearbyPoints(points:Point[],x:number,y:number,radius=24){
 return points.map(point=>({point,distance:Math.hypot(point.px-x,point.py-y)})).filter(p=>p.distance<=radius).sort((a,b)=>a.distance-b.distance||a.point.player.id.localeCompare(b.point.player.id)).map(p=>p.point);
}
export function previewPosition(x:number,y:number,width:number,height:number,cardWidth:number,cardHeight:number){
 const left=Math.max(8,Math.min(width-cardWidth-8,x+18)),below=height-y-26,above=y-26;
 const useBelow=cardHeight<=below||below>=above,maxHeight=Math.max(44,useBelow?below:above);
 const top=useBelow?y+18:Math.max(8,y-Math.min(cardHeight,maxHeight)-18);
 return {left,top,maxHeight};
}
