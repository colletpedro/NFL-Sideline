import catalog from './catalog.json';
export type MediaAsset = typeof catalog.candidates[number];
const urls = import.meta.glob('./candidates/*.png', { eager: true, query: '?url', import: 'default' }) as Record<string, string>;
export const candidates = catalog.candidates;
export const approvedForPublication = catalog.approvedForPublication;
export function candidateFor(team: string, type: 'helmet' | 'portrait') { return candidates.find(a => a.team === team && a.type === type); }
export function localSource(asset: MediaAsset) { return urls[`./candidates/${asset.team}-${asset.type}.png`] ?? ''; }
