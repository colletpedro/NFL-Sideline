import React,{Suspense,lazy} from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter,useSearchParams} from 'react-router-dom';
import SeasonApp from '../season/App';
import {StoryProvider} from '../game-story/Provider';
import {CurveProvider} from '../score-curve/Provider';
import '../journey.css';
import '../live-hub.css';
import '../situational/situational.css';
import '../reading-polish/polish.css';
import '../ranking-redzone/ranking-redzone.css';
import '../redzone-epa/redzone-epa.css';
import '../game-story/story.css';
import '../score-curve/curve.css';
const Questions=lazy(()=>import('./Entry'));
export function Entry(){const [q]=useSearchParams();return q.get('view')==='risk-lab'?<Suspense fallback={<p role="status">Abrindo laboratório…</p>}><Questions/></Suspense>:<StoryProvider><CurveProvider><SeasonApp labEnabled/></CurveProvider></StoryProvider>;}
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><Entry/></BrowserRouter></React.StrictMode>);
