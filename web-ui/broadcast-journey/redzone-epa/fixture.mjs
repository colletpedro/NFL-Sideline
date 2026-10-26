// Test-only private archive reader. Never imported by runtime components.
import {readFileSync} from 'node:fs';
export function epaFixture(){const root=process.env.NFL_REDZONE_EPA_QA_BUNDLE;return root?JSON.parse(readFileSync(root+'/redzone-epa.json','utf8')):null;}
