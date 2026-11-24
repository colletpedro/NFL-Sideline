import {createContext} from 'react';
import type {Story} from './model';
export type StoryState={data:Story|null;loading:boolean;error:string;retry:()=>void;weekly:boolean;setWeekly:(value:boolean)=>void};
export const GameStoryContext=createContext<StoryState|null>(null);
