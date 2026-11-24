import {createContext} from 'react';
import type {EpaData} from './model';
export type EpaState={data:EpaData|null;error:string;loading:boolean;retry:()=>void};
export const RedzoneEpaContext=createContext<EpaState|null>(null);
