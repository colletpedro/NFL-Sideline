import { useState } from 'react';
import { Logo } from '../../broadcast-experience/TeamLogo';
import { teamIdentity } from '../../broadcast-real/identity';
import { candidateFor, localSource, type MediaAsset } from './catalog';
function ImageOrIdentity({ asset, team, source, type }: { asset?: MediaAsset; team: string; source: string; type: 'helmet' | 'portrait' }) {
  const [failed, setFailed] = useState(false);
  return <div className={`media-frame media-${type}`} data-asset={asset?.assetId}>
    {asset && source && !failed ? <img src={source} alt={asset.type === 'portrait' ? `Retrato de ${asset.player}, associado a ${team} no roster 2026` : `Capacete ${team}, Riddell Authentic Speed padrão do catálogo`} width={asset.width} height={asset.height} loading={asset.type === 'portrait' ? 'lazy' : 'eager'} decoding="async" onError={() => setFailed(true)}/> : <div className="media-fallback"><Logo team={teamIdentity(team)}/><span>{teamIdentity(team).city} {teamIdentity(team).name}</span></div>}
  </div>;
}
export function TeamMedia({ team, type, allowCandidate = false, asset = candidateFor(team, type) }: { team: string; type: 'helmet' | 'portrait'; allowCandidate?: boolean; asset?: MediaAsset }) {
  // Only literal team/type associations may produce an image. Unknown rights are
  // previewed solely in the explicitly labelled local research surfaces.
  const valid = allowCandidate && asset?.team === team && asset.type === type && (type !== 'portrait' || !!asset.identifiers.gsis_id && asset.associationSeason === 2026);
  const source = valid && asset ? localSource(asset) : '';
  return <ImageOrIdentity key={`${team}|${type}|${source}`} asset={valid ? asset : undefined} team={team} source={source} type={type}/>;
}
