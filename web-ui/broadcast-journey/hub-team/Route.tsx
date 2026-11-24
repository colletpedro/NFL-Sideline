import {lazy,Suspense} from 'react';
import {useSearchParams} from 'react-router-dom';
import Legacy from '../App';
import W12App from '../w12/App';
import HubTeamApp from './App';
const Pilot=lazy(()=>import('../matchup/MatchupPage'));
export function Route(){const [q]=useSearchParams(),view=q.get('view');return view==='matchup-reading'?<Suspense fallback={<p role="status">Abrindo piloto…</p>}><Pilot/></Suspense>:view==='calendar-w12'?<W12App/>:['explorer','legacy'].includes(view??'')?<Legacy/>:<HubTeamApp/>;}
