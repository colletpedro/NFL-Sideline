import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {seasonBoundary} from './build/season';
import {storyBoundary} from './build/story';
import {curveBoundary} from './build/curve';
export default defineConfig(({command})=>({root:decodeURIComponent(new URL('./broadcast-journey',import.meta.url).pathname),cacheDir:decodeURIComponent(new URL('./node_modules/.vite-broadcast-curve-v2',import.meta.url).pathname),envFile:false,envPrefix:[],publicDir:decodeURIComponent(new URL('./public',import.meta.url).pathname),plugins:[{name:'story-entry',transformIndexHtml:{order:'pre',handler:html=>html.replace('src="/main.tsx"','src="/score-curve/main.tsx"')}},...(command==='serve'?[curveBoundary(18111),storyBoundary(18111),seasonBoundary(18111)]:[]),react()],server:{host:'127.0.0.1',port:18111,strictPort:true,cors:false,fs:{allow:[decodeURIComponent(new URL('.',import.meta.url).pathname)]}},build:{outDir:'../curve-dist',emptyOutDir:true,copyPublicDir:false}}));
