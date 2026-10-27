import {readFileSync} from 'node:fs';
export function fixture(){const root=process.env.NFL_SEASON_QA_BUNDLE;if(!root)return null;const load=p=>JSON.parse(readFileSync(root+'/'+p,'utf8'));const index=load('index.json');return {index,games:Object.fromEntries(index.games.map(g=>[g.gameId,load(g.path)])),teams:Object.fromEntries(index.teams.map(t=>[t.team,load(t.path)]))};}
