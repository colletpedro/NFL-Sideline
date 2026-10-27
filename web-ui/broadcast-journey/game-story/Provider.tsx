import {useEffect,useState} from 'react';
import {useSearchParams} from 'react-router-dom';
import {GameStoryContext} from './context';
import {loadStory,type Story} from './model';
export function StoryProvider({children}:{children:React.ReactNode}){const [q,setQ]=useSearchParams(),[retry,setRetry]=useState(0),[data,setData]=useState<Story|null>(null),[error,setError]=useState(''),[loading,setLoading]=useState(true);
 useEffect(()=>{const c=new AbortController();let active=true;setLoading(true);setError('');setData(null);loadStory(c.signal).then(d=>{if(active)setData(d);}).catch(e=>{if(active)setError(e instanceof Error?e.message:'Fonte indisponível.');}).finally(()=>{if(active)setLoading(false);});return()=>{active=false;c.abort();};},[retry]);
 return <GameStoryContext.Provider value={{data,loading,error,retry:()=>setRetry(n=>n+1),weekly:q.get('rank')==='week',setWeekly:value=>{const next=new URLSearchParams(q);next.set('rank',value?'week':'season');setQ(next,{preventScrollReset:true});}}}>{children}</GameStoryContext.Provider>;
}
