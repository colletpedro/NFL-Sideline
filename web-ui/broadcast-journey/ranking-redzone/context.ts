import {createContext,useContext} from 'react';
export const RankingRedzoneContext=createContext(false);
export const useRankingRedzone=()=>useContext(RankingRedzoneContext);
