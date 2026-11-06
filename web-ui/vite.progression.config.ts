import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {seasonBoundary} from './build/season';
import {storyBoundary} from './build/story';
import {curveBoundary} from './build/curve';
import {labBoundary} from './build/risk-lab';
import {outcomesBoundary} from './build/risk-outcomes';
import {progressionBoundary} from './build/progression';
const port=18127;
const base='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/';
export default defineConfig(({command})=>{
 if(command!=='serve')throw new Error('Progression is a local research server, not a public build.');
 return {root:decodeURIComponent(new URL('./broadcast-journey',import.meta.url).pathname),cacheDir:decodeURIComponent(new URL('./node_modules/.vite-progression',import.meta.url).pathname),envFile:false,envPrefix:[],publicDir:false,plugins:[{name:'progression-entry',transformIndexHtml:{order:'pre',handler:html=>html.replace('src="/main.tsx"','src="/risk-outcomes/main.tsx"')}},labBoundary(process.env.NFL_RISK_LAB_STORE??base+'qb-risk-lab-v1',port),outcomesBoundary(process.env.NFL_RISK_OUTCOMES_STORE??base+'qb-risk-outcomes-lab-v1',port),progressionBoundary(process.env.NFL_PROGRESSION_STORE??base+'qb-progression-improvisation-lab-v1',port),curveBoundary(port),storyBoundary(port),seasonBoundary(port),react()],server:{host:'127.0.0.1',port,strictPort:true,cors:false,fs:{allow:[decodeURIComponent(new URL('.',import.meta.url).pathname)]}}};
});
