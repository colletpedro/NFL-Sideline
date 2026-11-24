import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter} from 'react-router-dom';
import {Entry} from './Entry';
import '../journey.css';
import '../live-hub.css';
import '../situational/situational.css';
import '../reading-polish/polish.css';
import './ranking-redzone.css';

ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><Entry/></BrowserRouter></React.StrictMode>);
