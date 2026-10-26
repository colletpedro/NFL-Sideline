import {useEffect,useState} from 'react';
import {RedzoneEpaContext,type EpaState} from './context';
import {loadEpa} from './model';
export function RedzoneEpaProvider({children}:{children:React.ReactNode}) {
 const [revision,setRevision]=useState(0),[state,setState]=useState<Omit<EpaState,'retry'>>({data:null,error:'',loading:true});
 useEffect(()=>{const controller=new AbortController();let active=true;setState({data:null,error:'',loading:true});loadEpa(controller.signal).then(data=>{if(active)setState({data,error:'',loading:false});}).catch(error=>{if(active)setState({data:null,error:error instanceof Error?error.message:'Fonte de EPA indisponível.',loading:false});});return()=>{active=false;controller.abort();};},[revision]);
 return <RedzoneEpaContext.Provider value={{...state,retry:()=>setRevision(v=>v+1)}}>{children}</RedzoneEpaContext.Provider>;
}
