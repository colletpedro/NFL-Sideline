// Test-only operator fixture loader. Never imported by an application entry point.
import { readFileSync } from 'node:fs';
export function loadRealFixture() {
  const root=process.env.NFL_SITUATIONAL_QA_BUNDLE;
  if (!root) return null;
  const data=JSON.parse(readFileSync(`${root}/situational.json`,'utf8'));
  const marker=JSON.parse(readFileSync(`${root}/COMPLETED.json`,'utf8'));
  const audit=JSON.parse(readFileSync(new URL('../../../docs/plans/broadcast-situational-w12-v1/reconciliation.json',import.meta.url),'utf8'));
  return {data,bundleId:marker.bundleId,rounded:audit.rounded};
}
