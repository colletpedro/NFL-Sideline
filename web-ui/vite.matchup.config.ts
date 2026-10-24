import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { situationalBoundary } from './build/situational';
import { observationBoundary } from './build/observations';
import { matchupBoundary } from './build/matchup';
import { matchupPort } from './build/matchup-process.mjs';
export default defineConfig(({command}) => {
  const port=matchupPort();
  return {root:decodeURIComponent(new URL('./broadcast-journey',import.meta.url).pathname),envFile:false,envPrefix:[],
    publicDir:decodeURIComponent(new URL('./public',import.meta.url).pathname),
    plugins:[...(command==='serve'?[observationBoundary(port),situationalBoundary(port),matchupBoundary(port)]:[]),react()],
    server:{host:'127.0.0.1',port,strictPort:true,cors:false,fs:{allow:[decodeURIComponent(new URL('.',import.meta.url).pathname)]}},
    build:{outDir:'../matchup-dist',emptyOutDir:true,copyPublicDir:false}};
});
