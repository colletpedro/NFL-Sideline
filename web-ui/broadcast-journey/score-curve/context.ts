import {createContext} from 'react';
import type {CurveEvents} from './model';
export type CurveState={data:CurveEvents|null;loading:boolean;error:string;retry:()=>void};
export const CurveContext=createContext<CurveState|null>(null);
