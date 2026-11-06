import type {Player} from './model';
export function scatter(players:Player[],width:number,fontScale=1){
 const available=players.filter(p=>p.comparisons.main.a.meanEpa!==null&&p.comparisons.main.b.meanEpa!==null),values=available.flatMap(p=>[p.comparisons.main.a.meanEpa!,p.comparisons.main.b.meanEpa!]),low=Math.min(0,...values),high=Math.max(0,...values),targetTicks=Math.max(2,Math.min(5,Math.floor((width-50*fontScale-22)/(62*fontScale)))),raw=Math.max(.2,(high-low)*1.12/targetTicks),power=10**Math.floor(Math.log10(raw)),step=[1,2,5,10].map(x=>x*power).find(x=>x>=raw)!,min=Math.floor((low-.08*(high-low))/step)*step,max=Math.max(min+step,Math.ceil((high+.08*(high-low))/step)*step),bounds={left:50*fontScale,top:24,width:Math.max(110,width-50*fontScale-22),height:Math.max(270,Math.min(450,width*.44))};
 const x=(v:number)=>bounds.left+(v-min)/(max-min)*bounds.width,y=(v:number)=>bounds.top+bounds.height-(v-min)/(max-min)*bounds.height;
 return {min,max,step,bounds,x,y,height:bounds.top+bounds.height+34*fontScale,points:available.map(player=>({player,x:player.comparisons.main.b.meanEpa!,y:player.comparisons.main.a.meanEpa!,px:x(player.comparisons.main.b.meanEpa!),py:y(player.comparisons.main.a.meanEpa!)}))};
}
export type Point=ReturnType<typeof scatter>['points'][number];
export function nearby(points:Point[],x:number,y:number){return points.map(p=>({p,d:Math.hypot(p.px-x,p.py-y)})).filter(p=>p.d<=26).sort((a,b)=>a.d-b.d||a.p.player.id.localeCompare(b.p.player.id)).map(v=>v.p);}
