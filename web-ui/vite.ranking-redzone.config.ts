import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {observationBoundary} from './build/observations';
import {situationalBoundary} from './build/situational';
import {matchupBoundary} from './build/matchup';
import {w12Boundary} from './build/w12';
import {teamBoundary} from './build/team';
export default defineConfig(({command})=>({root:decodeURIComponent(new URL('./broadcast-journey',import.meta.url).pathname),cacheDir:decodeURIComponent(new URL('./node_modules/.vite-broadcast-ranking-redzone-v1',import.meta.url).pathname),envFile:false,envPrefix:[],publicDir:decodeURIComponent(new URL('./public',import.meta.url).pathname),plugins:[{name:'ranking-redzone-entry',transformIndexHtml:{order:'pre',handler:html=>html.replace('src="/main.tsx"','src="/ranking-redzone/main.tsx"')}},...(command==='serve'?[teamBoundary(18107),w12Boundary(18107),observationBoundary(18107),situationalBoundary(18107),matchupBoundary(18107)]:[]),react()],server:{host:'127.0.0.1',port:18107,strictPort:true,cors:false,fs:{allow:[decodeURIComponent(new URL('.',import.meta.url).pathname)]}},build:{outDir:'../ranking-redzone-dist',emptyOutDir:true,copyPublicDir:false}}));
