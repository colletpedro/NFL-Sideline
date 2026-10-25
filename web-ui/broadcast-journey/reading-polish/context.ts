import {createContext,useContext} from 'react';
export const ReadingPolishContext=createContext(false);
export const useReadingPolish=()=>useContext(ReadingPolishContext);
