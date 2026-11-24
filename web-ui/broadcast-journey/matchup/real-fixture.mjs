// Test-only fixture acquisition. No application imports this module.
import { readFileSync } from 'node:fs';
export function comparisonFixture() {
  const root=process.env.NFL_MATCHUP_QA_BUNDLE;
  if(!root)return null;
  return {data:JSON.parse(readFileSync(root+'/comparison.json','utf8')),marker:JSON.parse(readFileSync(root+'/COMPLETED.json','utf8')),
    manifest:JSON.parse(readFileSync(new URL('../../public/data/manifest.json',import.meta.url),'utf8')),
    calendar:JSON.parse(readFileSync(new URL('../../public/data/seasons/2026.json',import.meta.url),'utf8')),
    expected:JSON.parse(readFileSync(new URL('../../../docs/plans/broadcast-matchup-reading-v1/checks/numerical-oracle.json',import.meta.url),'utf8'))};
}
