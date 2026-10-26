export const EPA_ENDPOINT='/__redzone-epa/';
export const EPA_PIN='sha256:6e6bffd6d2e8fc1e70e9d47e395f250b8dcf2cbc084bedbf4e4a32fb2ccf8af6';
export const EPA_RULE='classified-scrimmage-redzone-start-v1';
export const EPA_SOURCE_PIN='sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc';
export type Rational={numerator:string;denominator:string};
export type Status='AVAILABLE'|'NO_OPPORTUNITIES'|'INSUFFICIENT'|'SOURCE_ABSENT';
export type Unit={id:string;gameId:string;week:number;playId:number;sourceOrder:number;offense:string;defense:string;yardline:number;kind:'pass'|'run';sack:boolean;scramble:boolean;epa:string|null;epaStatus:'VALID'|'MISSING'|'NONFINITE'};
export type Reading={status:Status;eligibleN:number;validN:number;missingN:number;nonfiniteN:number;ambiguityN:number;sum:Rational;mean:Rational|null;units:Unit[];exclusions:Record<string,number>;gameIds:string[];weeks:number[]};
export type GameReading=Reading&{offense:string;defense:string};
export type TeamReading=Reading&{perspective:'off'|'def';components:{gameId:string;week:number;status:Status;validN:number;sum:Rational;mean:Rational|null}[]};
export type EpaData={contractVersion:string;rule:string;sourcePin:string;pbpHash:string;season:number;phase:string;weeks:number[];guarantees:Record<string,string>;policy:Record<string,string|boolean>;games:Record<string,{gameId:string;week:number;away:string;home:string;productions:GameReading[]}>;teams:Record<string,{team:string;productions:TeamReading[]}>};
function assert(ok:unknown):asserts ok {if(!ok)throw new Error('A fonte de EPA da red zone não passou na validação.');}
function gcd(a:bigint,b:bigint):bigint {a=a<0n?-a:a;while(b){const r=a%b;a=b;b=r;}return a;}
function norm(n:bigint,d:bigint):Rational {const g=gcd(n,d);return {numerator:String(n/g),denominator:String(d/g)};}
function add(a:Rational,b:Rational){return norm(BigInt(a.numerator)*BigInt(b.denominator)+BigInt(b.numerator)*BigInt(a.denominator),BigInt(a.denominator)*BigInt(b.denominator));}
function exact(v:string):Rational {assert(/^-?\d+(\.\d+)?([eE][+-]?\d+)?$/.test(v)&&Number.isFinite(Number(v)));const [mantissa,power='0']=v.toLowerCase().split('e'),[whole,fraction='']=mantissa.split('.'),exp=Number(power)-fraction.length,n=BigInt(whole+fraction);return exp>=0?norm(n*10n**BigInt(exp),1n):norm(n,10n**BigInt(-exp));}
function equal(a:Rational,b:Rational) {return BigInt(a.numerator)*BigInt(b.denominator)===BigInt(b.numerator)*BigInt(a.denominator);}
function rational(v:Rational) {assert(v&&/^-?\d+$/.test(v.numerator)&&/^[1-9]\d*$/.test(v.denominator));}
export function value(r:Reading) {return r.status==='AVAILABLE'&&r.mean?Number(r.mean.numerator)/Number(r.mean.denominator):null;}
export function epaLabel(v:number) {const rounded=Math.round(Math.abs(v)*1000)/1000;return `${rounded===0?'':v>0?'+':'−'}${rounded.toFixed(3).replace('.',',')}`;}
export function validateReading(r:Reading) {
 assert(r&&['AVAILABLE','NO_OPPORTUNITIES','INSUFFICIENT','SOURCE_ABSENT'].includes(r.status)&&Array.isArray(r.units));
 for(const n of [r.eligibleN,r.validN,r.missingN,r.nonfiniteN,r.ambiguityN,...Object.values(r.exclusions)])assert(Number.isSafeInteger(n)&&n>=0);
 assert(r.eligibleN===r.units.length&&r.validN+r.missingN+r.nonfiniteN===r.eligibleN&&new Set(r.units.map(u=>u.id)).size===r.units.length);
 rational(r.sum);let total:Rational={numerator:'0',denominator:'1'};let valid=0,missing=0,nonfinite=0;
 for(const u of r.units){assert(u.id===`${u.gameId}:${u.playId}`&&/^2026_0[12]_[A-Z]{2,3}_[A-Z]{2,3}$/.test(u.gameId)&&[1,2].includes(u.week)&&Number.isSafeInteger(u.playId)&&Number.isFinite(u.sourceOrder)&&u.yardline>0&&u.yardline<=20&&['pass','run'].includes(u.kind)&&typeof u.sack==='boolean'&&typeof u.scramble==='boolean');if(u.epaStatus==='VALID'){assert(typeof u.epa==='string');total=add(total,exact(u.epa));valid++;}else{assert(u.epa===null&&['MISSING','NONFINITE'].includes(u.epaStatus));if(u.epaStatus==='MISSING')missing++;else nonfinite++;}}
 assert(valid===r.validN&&missing===r.missingN&&nonfinite===r.nonfiniteN&&equal(total,r.sum));
 if(r.status==='AVAILABLE'){assert(r.ambiguityN===0&&valid>0&&r.mean);rational(r.mean);assert(equal(r.mean,norm(BigInt(total.numerator),BigInt(total.denominator)*BigInt(valid)))&&Number.isFinite(value(r)));}
 else assert(r.mean===null);
 if(r.status==='NO_OPPORTUNITIES')assert(r.eligibleN===0&&r.ambiguityN===0);
 return r;
}
export function validateEpaData(input:unknown):EpaData {
 const d=input as EpaData;assert(d&&d.contractVersion==='broadcast-redzone-epa-v1'&&d.rule===EPA_RULE&&d.sourcePin===EPA_SOURCE_PIN&&d.season===2026&&d.phase==='REG'&&JSON.stringify(d.weeks)==='[1,2]');
 assert(d.policy.leagueReference===false&&d.policy.prediction===false&&d.policy.qualitySuperiority===false&&d.policy.sideBySide==='SAME_RULE_SOURCE_PERIOD_AVAILABLE_ONLY');
 assert(['completeness','expectedCoverage','epaModel','historicalAvailability'].every(k=>d.guarantees[k]==='UNKNOWN'));
 const games=Object.values(d.games);assert(games.length===32&&Object.keys(d.teams).length===32);
 for(const [id,g] of Object.entries(d.games)){assert(id===g.gameId&&g.productions.length===2&&[1,2].includes(g.week));for(const [i,p] of g.productions.entries()){validateReading(p);assert(p.offense===[g.away,g.home][i]&&p.defense===[g.home,g.away][i]&&p.gameIds.join()===id&&p.weeks.join()===String(g.week));assert(p.units.every(u=>u.gameId===id&&u.week===g.week&&u.offense===p.offense&&u.defense===p.defense));}}
 for(const [team,t] of Object.entries(d.teams)){assert(t.team===team&&t.productions.length===2);for(const [i,p] of t.productions.entries()){validateReading(p);assert(p.perspective===['off','def'][i]&&p.components.length===2&&p.weeks.join()==='1,2'&&p.gameIds.length===2);const members=p.gameIds.map(id=>d.games[id]?.productions.find(m=>m[i===0?'offense':'defense']===team));assert(members.every(Boolean));const units=members.flatMap(m=>m!.units);assert(p.units.length===units.length&&p.units.every(u=>units.some(v=>JSON.stringify(u)===JSON.stringify(v))));for(const [j,c] of p.components.entries()){const m=members[j]!;assert(c.gameId===p.gameIds[j]&&c.week===j+1&&c.status===m.status&&c.validN===m.validN&&equal(c.sum,m.sum)&&JSON.stringify(c.mean)===JSON.stringify(m.mean));}const blocked=members.some(m=>m!.status==='INSUFFICIENT'||m!.status==='SOURCE_ABSENT');assert(!blocked||p.mean===null);}}
 return d;
}
export async function loadEpa(signal?:AbortSignal):Promise<EpaData> {
 const response=await fetch(EPA_ENDPOINT,{method:'GET',headers:{'X-Local-Redzone-Epa':'1','X-Redzone-Epa-Collection':EPA_PIN},signal,cache:'no-store',redirect:'error'});
 if(!response.ok)throw new Error('A fonte local de EPA da red zone está indisponível. As campanhas continuam acessíveis.');
 const text=await response.text(),bytes=await crypto.subtle.digest('SHA-256',new TextEncoder().encode(text)),hash='sha256:'+Array.from(new Uint8Array(bytes),x=>x.toString(16).padStart(2,'0')).join('');
 assert(hash===EPA_PIN&&response.headers.get('X-Redzone-Epa-Collection')===EPA_PIN);
 return validateEpaData(JSON.parse(text));
}
