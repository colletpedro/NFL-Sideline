import {readFileSync} from 'node:fs';
export function fixture(){const root=process.env.NFL_STORY_QA_BUNDLE;if(!root)return null;const load=p=>JSON.parse(readFileSync(root+'/'+p,'utf8'));return {data:load('story.json'),game:load('source/games/2026_07_CIN_BAL.json')};}
