import {readFileSync} from 'node:fs';
import {join} from 'node:path';
export function fixture(){const p=process.env.NFL_CURVE_QA_BUNDLE;return p?{extra:JSON.parse(readFileSync(join(p,'events.json'),'utf8')),story:JSON.parse(readFileSync(join(p,'source/story.json'),'utf8'))}:null;}
