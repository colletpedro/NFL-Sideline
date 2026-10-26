import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {observationBoundary} from './build/observations';
import {situationalBoundary} from './build/situational';
import {matchupBoundary} from './build/matchup';
import {w12Boundary} from './build/w12';
import {teamBoundary} from './build/team';
import {redzoneEpaBoundary} from './build/redzone-epa';
export default defineConfig(({command})=>({root:decodeURIComponent(new URL('./broadcast-journey',import.meta.url).pathname),cacheDir:decodeURIComponent(new URL('./node_modules/.vite-broadcast-redzone-epa-v1',import.meta.url).pathname),envFile:false,envPrefix:[],publicDir:decodeURIComponent(new URL('./public',import.meta.url).pathname),plugins:[{name:'redzone-epa-entry',transformIndexHtml:{order:'pre',handler:html=>html.replace('src="/main.tsx"','src="/redzone-epa/main.tsx"')}},...(command==='serve'?[redzoneEpaBoundary(18108),teamBoundary(18108),w12Boundary(18108),observationBoundary(18108),situationalBoundary(18108),matchupBoundary(18108)]:[]),react()],server:{host:'127.0.0.1',port:18108,strictPort:true,cors:false,fs:{allow:[decodeURIComponent(new URL('.',import.meta.url).pathname)]}},build:{outDir:'../redzone-epa-dist',emptyOutDir:true,copyPublicDir:false}}));
