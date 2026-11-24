import React, { lazy, Suspense } from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter, useSearchParams } from 'react-router-dom';
import App from '../App';
import W12App from './App';
import '../journey.css';
import '../live-hub.css';
import '../situational/situational.css';
const Pilot=lazy(()=>import('../matchup/MatchupPage'));
export function Route() {const [q]=useSearchParams();const view=q.get('view');return view==='matchup-reading'?<Suspense fallback={<p role="status">Abrindo piloto…</p>}><Pilot/></Suspense>:view===null||view==='matchup-w12'?<W12App/>:<App/>;}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><Route/></BrowserRouter></React.StrictMode>);
