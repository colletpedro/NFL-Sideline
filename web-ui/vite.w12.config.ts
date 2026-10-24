import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { observationBoundary } from './build/observations';
import { situationalBoundary } from './build/situational';
import { matchupBoundary } from './build/matchup';
import { w12Boundary } from './build/w12';
export default defineConfig(({command})=>({root:decodeURIComponent(new URL('./broadcast-journey',import.meta.url).pathname),envFile:false,envPrefix:[],
  publicDir:decodeURIComponent(new URL('./public',import.meta.url).pathname),
  plugins:[{name:'w12-entry',transformIndexHtml:html=>html.replace('src="/main.tsx"','src="/w12/main.tsx"')},...(command==='serve'?[w12Boundary(18104),observationBoundary(18104),situationalBoundary(18104),matchupBoundary(18104)]:[]),react()],
  server:{host:'127.0.0.1',port:18104,strictPort:true,cors:false,fs:{allow:[decodeURIComponent(new URL('.',import.meta.url).pathname)]}},
  build:{outDir:'../w12-dist',emptyOutDir:true,copyPublicDir:false}}));
