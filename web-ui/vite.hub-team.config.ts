import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {observationBoundary} from './build/observations';
import {situationalBoundary} from './build/situational';
import {matchupBoundary} from './build/matchup';
import {w12Boundary} from './build/w12';
import {teamBoundary} from './build/team';
export default defineConfig(({command})=>({root:decodeURIComponent(new URL('./broadcast-journey',import.meta.url).pathname),cacheDir:decodeURIComponent(new URL('./node_modules/.vite-broadcast-hub-team-w12-v1',import.meta.url).pathname),envFile:false,envPrefix:[],publicDir:decodeURIComponent(new URL('./public',import.meta.url).pathname),plugins:[{name:'hub-team-entry',transformIndexHtml:{order:'pre',handler:html=>html.replace('src="/main.tsx"','src="/hub-team/main.tsx"')}},...(command==='serve'?[teamBoundary(18105),w12Boundary(18105),observationBoundary(18105),situationalBoundary(18105),matchupBoundary(18105)]:[]),react()],server:{host:'127.0.0.1',port:18105,strictPort:true,cors:false,fs:{allow:[decodeURIComponent(new URL('.',import.meta.url).pathname)]}},build:{outDir:'../hub-team-dist',emptyOutDir:true,copyPublicDir:false}}));
