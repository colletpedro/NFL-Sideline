import type {Point} from '../w12/model';
import {compareObservedRates} from '../reading-polish/rates';
export const POSITION_RULE='broadcast-observed-rate-position-1.0.0';
export function observedPositions(points:Point[]) {
 if(new Set(points.map(p=>p.team)).size!==points.length||points.some(p=>p.status!=='AVAILABLE'||!Number.isSafeInteger(p.numerator)||!Number.isSafeInteger(p.denominator)||p.denominator<=0||p.numerator<0||p.numerator>p.denominator))throw new Error('Inventário incompatível com posições descritivas.');
 const ordered=[...points].sort(compareObservedRates);
 let position=0;
 return ordered.map((point,i)=>{const previous=ordered[i-1];if(!previous||BigInt(previous.numerator)*BigInt(point.denominator)!==BigInt(point.numerator)*BigInt(previous.denominator))position=i+1;return {point,position};});
}
