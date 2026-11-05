import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {seasonBoundary} from './build/season';
import {storyBoundary} from './build/story';
import {curveBoundary} from './build/curve';
import {labBoundary} from './build/risk-lab';
import {outcomesBoundary} from './build/risk-outcomes';
import {outcomesExport} from './build/risk-outcomes-export';
const port=18125;
const m3=process.env.NFL_RISK_LAB_STORE??'/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-lab-v1';
const b2=process.env.NFL_RISK_OUTCOMES_STORE??'/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-outcomes-lab-v1';
export default defineConfig(({command})=>({root:decodeURIComponent(new URL('./broadcast-journey',import.meta.url).pathname),cacheDir:decodeURIComponent(new URL('./node_modules/.vite-risk-outcomes',import.meta.url).pathname),envFile:false,envPrefix:[],publicDir:false,
 plugins:[{name:'risk-outcomes-entry',transformIndexHtml:{order:'pre',handler:html=>html.replace('src="/main.tsx"','src="/risk-outcomes/main.tsx"')}},...(command==='serve'?[labBoundary(m3,port),outcomesBoundary(b2,port),curveBoundary(port),storyBoundary(port),seasonBoundary(port)]:[outcomesExport(m3,b2)]),react()],server:{host:'127.0.0.1',port,strictPort:true,cors:false,fs:{allow:[decodeURIComponent(new URL('.',import.meta.url).pathname)]}},build:{outDir:'../risk-outcomes-dist',emptyOutDir:true,copyPublicDir:false}}));
