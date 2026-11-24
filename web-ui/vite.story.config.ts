import {defineConfig} from 'vite';
import react from '@vitejs/plugin-react';
import {seasonBoundary} from './build/season';
import {storyBoundary} from './build/story';
export default defineConfig(({command})=>({root:decodeURIComponent(new URL('./broadcast-journey',import.meta.url).pathname),cacheDir:decodeURIComponent(new URL('./node_modules/.vite-broadcast-story-v1',import.meta.url).pathname),envFile:false,envPrefix:[],publicDir:decodeURIComponent(new URL('./public',import.meta.url).pathname),plugins:[{name:'story-entry',transformIndexHtml:{order:'pre',handler:html=>html.replace('src="/main.tsx"','src="/game-story/main.tsx"')}},...(command==='serve'?[storyBoundary(18110),seasonBoundary(18110)]:[]),react()],server:{host:'127.0.0.1',port:18110,strictPort:true,cors:false,fs:{allow:[decodeURIComponent(new URL('.',import.meta.url).pathname)]}},build:{outDir:'../story-dist',emptyOutDir:true,copyPublicDir:false}}));
