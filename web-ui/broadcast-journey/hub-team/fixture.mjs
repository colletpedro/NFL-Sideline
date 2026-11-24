// Test-only. Not imported by the application.
import {readFileSync} from 'node:fs';
export function teamFixture(){const root=process.env.NFL_TEAM_QA_BUNDLE;if(!root)return null;const load=p=>JSON.parse(readFileSync(root+'/'+p,'utf8'));return {index:load('index.json'),docs:Object.fromEntries(load('index.json').teams.map(e=>[e.team,load(e.path)])),matchupIndex:load('source/matchups/index.json'),oracle:JSON.parse(readFileSync(new URL('../../../docs/plans/broadcast-hub-team-w12-v1/checks/reconciliation.json',import.meta.url),'utf8'))};}
