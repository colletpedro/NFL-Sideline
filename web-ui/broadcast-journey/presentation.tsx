import {createContext,useContext} from 'react';
import {gameHref,teamHref,weekHref} from './hub-team/model';
export const PresentationContext=createContext({weeks:[1,2],period:'W1–2',defaultWeek:1,pin:'',redzonePin:'',gameHref,teamHref,weekHref});
export const usePresentation=()=>useContext(PresentationContext);
