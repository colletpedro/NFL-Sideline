import type {Point} from '../w12/model';
export function compareObservedRates(a:Point,b:Point) {
 const difference=BigInt(b.numerator)*BigInt(a.denominator)-BigInt(a.numerator)*BigInt(b.denominator);
 return difference>0n?1:difference<0n?-1:a.team.localeCompare(b.team);
}
