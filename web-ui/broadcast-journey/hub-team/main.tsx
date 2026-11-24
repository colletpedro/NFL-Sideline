import React from 'react';
import ReactDOM from 'react-dom/client';
import {BrowserRouter} from 'react-router-dom';
import {Route} from './Route';
import '../journey.css';
import '../live-hub.css';
import '../situational/situational.css';
ReactDOM.createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><Route/></BrowserRouter></React.StrictMode>);
