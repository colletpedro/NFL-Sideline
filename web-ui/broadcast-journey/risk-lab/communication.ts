import type {Counts,Player} from './model';
export const metricLabels={classified:'Passes classificados como interceptáveis',expected:'Passes interceptáveis esperados',interceptions:'Interceptações sofridas'};
export type Scale='total'|'per100';
export const number=(x:number,d=1)=>(Math.abs(x)<.5*10**-d?0:x).toLocaleString('pt-BR',{minimumFractionDigits:d,maximumFractionDigits:d});
export const signed=(x:number,d=1)=>(x>=.5*10**-d?'+':'')+number(x,d);
export function shortName(name:string){const parts=name.split(' ');return parts.length===1?name:parts[0][0]+'. '+parts.slice(1).join(' ');}
export function coordinates(p:Counts,scale:Scale){if(p.passes===0)return null;const denominator=scale==='per100'?p.passes/100:1;return {x:p.expected/denominator,y:p.observed/denominator};}
export function domainFor(players:Player[],scale:Scale){const max=Math.max(0,...players.flatMap(p=>{const c=coordinates(p,scale);return c?[c.x,c.y]:[];}));if(!max)return {max:1,step:.2};const raw=max*1.08/5,power=10**Math.floor(Math.log10(raw)),step=[1,2,5,10].map(v=>v*power).find(v=>v>=raw)!;return {max:Math.ceil(max*1.08/step)*step,step};}
export type Point={player:Player;x:number;y:number;px:number;py:number};
export type Group={id:string;members:Point[];anchorX:number;anchorY:number;left:number;top:number;width:number;height:number;compact:boolean;label:string};
export function scatterLayout(players:Player[],scale:Scale,width:number,fontScale=1){
 const bounds={left:42,top:18,size:Math.max(160,width-66)},domain=domainFor(players,scale);
 const points=players.flatMap(player=>{const c=coordinates(player,scale);return c?[{player,...c,px:bounds.left+c.x/domain.max*bounds.size,py:bounds.top+bounds.size-c.y/domain.max*bounds.size}]:[];});
 // Bounded proximity groups, without transitive chaining. Statistical coordinates never move.
 const components:Point[][]=[];const remaining=new Set(points);
 for(const seed of [...points].sort((a,b)=>b.y-a.y||a.player.id.localeCompare(b.player.id))){if(!remaining.delete(seed))continue;const members=[seed];for(const candidate of remaining)if(Math.hypot(seed.px-candidate.px,seed.py-candidate.py)<44){remaining.delete(candidate);members.push(candidate);}components.push(members);}
 const used:{left:number;top:number;width:number;height:number}[]=[];
 const intersects=(a:typeof used[number],b:typeof used[number])=>a.left<b.left+b.width+4&&a.left+a.width+4>b.left&&a.top<b.top+b.height+4&&a.top+a.height+4>b.top;
 const groups:Group[]=components.sort((a,b)=>Math.max(...b.map(p=>p.y))-Math.max(...a.map(p=>p.y))).map((members,i)=>{
  members.sort((a,b)=>a.player.id.localeCompare(b.player.id));const anchorX=members.reduce((s,p)=>s+p.px,0)/members.length,anchorY=members.reduce((s,p)=>s+p.py,0)/members.length;
  const label=members.length===1?shortName(members[0].player.name)+(members[0].player.teams.length>1?' · '+members[0].player.teams.join('/'):''):`#${i+1} · ${members.length} jogadores`;
  const desiredWidth=width>=600?Math.max(110,label.length*7*fontScale+34):44,height=44;
  function candidates(w:number){const result:{left:number;top:number;width:number;height:number}[]=[];for(let y=bounds.top;y<=bounds.top+bounds.size-height;y+=48)for(let x=4;x<=width-w-4;x+=w+8)result.push({left:x,top:y,width:w,height});return result.sort((a,b)=>Math.hypot(a.left+w/2-anchorX,a.top+22-anchorY)-Math.hypot(b.left+w/2-anchorX,b.top+22-anchorY));}
  function free(r:typeof used[number]){return !used.some(u=>intersects(r,u))&&!points.some(p=>p.px>r.left-5&&p.px<r.left+r.width+5&&p.py>r.top-5&&p.py<r.top+r.height+5);}
  let rect=candidates(desiredWidth).find(free),compact=width<600;
  if(!rect){rect=candidates(44).find(r=>!used.some(u=>intersects(r,u)));compact=true;}
  if(!rect){const columns=Math.max(1,Math.floor((width-8)/48)),overflow=used.filter(r=>r.top>bounds.top+bounds.size).length;rect={left:4+(overflow%columns)*48,top:bounds.top+bounds.size+40+Math.floor(overflow/columns)*48,width:44,height};compact=true;}
  used.push(rect);return {id:members[0].player.id,members,anchorX,anchorY,...rect,compact,label:compact?String(i+1):label};
 });return {bounds,domain,points,groups,height:Math.max(bounds.top+bounds.size+32,...used.map(r=>r.top+r.height+8))};
}
