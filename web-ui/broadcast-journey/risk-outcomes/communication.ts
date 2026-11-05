import type {OutcomeCounts,OutcomePlayer} from './model';
import {number,signed} from '../risk-lab/communication';
export const interceptionNumber=(x:number)=>number(x,x!==0&&Math.abs(x)<.005?4:2);
export const interceptionSigned=(x:number)=>signed(x,x!==0&&Math.abs(x)<.005?4:2);
export const outcomeLabels={observed:'Interceptações sofridas',expected:'Interceptações esperadas',difference:'Sofridas menos esperadas'};
export type OutcomeScale='total'|'per100';
export function outcomeCoordinates(p:OutcomeCounts,scale:OutcomeScale){if(!p.eligiblePasses)return null;const den=scale==='per100'?p.eligiblePasses/100:1;return {x:p.expectedInterceptions/den,y:p.observedInterceptions/den};}
export function outcomeDomain(players:OutcomePlayer[],scale:OutcomeScale){const max=Math.max(0,...players.flatMap(p=>{const c=outcomeCoordinates(p,scale);return c?[c.x,c.y]:[];}));if(!max)return {max:1,step:.2};const raw=max*1.08/5,power=10**Math.floor(Math.log10(raw)),step=[1,2,5,10].map(v=>v*power).find(v=>v>=raw)!;return {max:Math.ceil(max*1.08/step)*step,step};}
export function outcomeLayout(players:OutcomePlayer[],scale:OutcomeScale,width:number,fontScale=1){const bounds={left:42*fontScale,top:24,width:Math.max(120,width-42*fontScale-24),height:Math.max(260,Math.min(440,width*.43))},domain=outcomeDomain(players,scale),points=players.flatMap(player=>{const c=outcomeCoordinates(player,scale);return c?[{player,...c,px:bounds.left+c.x/domain.max*bounds.width,py:bounds.top+bounds.height-c.y/domain.max*bounds.height}]:[];});return {bounds,domain,points,height:bounds.top+bounds.height+32*fontScale};}
export type OutcomePoint=ReturnType<typeof outcomeLayout>['points'][number];
export function nearbyOutcomes(points:OutcomePoint[],x:number,y:number,radius=24){return points.map(point=>({point,distance:Math.hypot(point.px-x,point.py-y)})).filter(p=>p.distance<=radius).sort((a,b)=>a.distance-b.distance||a.point.player.id.localeCompare(b.point.player.id)).map(p=>p.point);}
