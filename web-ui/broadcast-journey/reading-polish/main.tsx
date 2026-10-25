import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter,useSearchParams} from 'react-router-dom';
import {Route} from '../hub-team/Route';
import {ReadingPolishContext} from './context';
import '../journey.css';
import '../live-hub.css';
import '../situational/situational.css';
import './polish.css';
function Entry(){const [q]=useSearchParams();const enabled=[null,'matchup-w12','team-w12'].includes(q.get('view'));return <ReadingPolishContext.Provider value={enabled}><div className={enabled?'rp':undefined}><Route/></div></ReadingPolishContext.Provider>;}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><Entry/></BrowserRouter></React.StrictMode>);
