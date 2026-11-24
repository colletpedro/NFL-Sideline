import {readFileSync} from 'node:fs';
export const positionOracle=JSON.parse(readFileSync(new URL('../../../docs/plans/broadcast-ranking-redzone-v1/checks/representation.json',import.meta.url),'utf8'));
