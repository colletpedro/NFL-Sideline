import { useState, type CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import { Logo } from '../../broadcast-experience/TeamLogo';
import { teamIdentity } from '../../broadcast-real/identity';
import { journeyHref } from '../state';
import { TeamMedia } from './Media';
import { candidates, approvedForPublication, candidateFor } from './catalog';
export function MediaGallery({ q }: { q: URLSearchParams }) {
  const [fallback, setFallback] = useState(false), [retryTeam, setRetryTeam] = useState('BAL');
  return <div className="media-gallery">
    <p className="media-intro">Quatro identidades, duas famílias de imagens. Fotografias para pesquisa local; não comprovam participação em jogo, titularidade ou desempenho.</p>
    <section className="media-status"><h2>Utilização qualificada para publicação</h2><p>{approvedForPublication.length} dos oito novos ativos. Nenhuma licença específica de redistribuição foi estabelecida.</p><p>Os 32 logos locais anteriores continuam preservados no <a href="/logos.html">painel de identidades</a>, com sua procedência anterior.</p></section>
    <div className="media-gallery-heading"><h2>Candidatos de pesquisa local</h2><p>{candidates.length} arquivos obtidos e validados · condições gerais documentadas · permissão de reutilização não verificada</p></div>
    <div className="media-gallery-grid">{['DAL', 'NE', 'BAL', 'IND'].map(team => {
      const visual = teamIdentity(team);
      return <section key={team} className="media-team" style={{ '--team': visual.color, '--team-dark': visual.dark } as CSSProperties}>
        <header><Logo team={visual}/><h3><span>{visual.city} · {team}</span>{visual.name}</h3></header>
        {(['helmet','portrait'] as const).map(type => { const asset = candidateFor(team,type)!; return <figure key={type}>
          <TeamMedia team={team} type={type} allowCandidate/>
          <figcaption><h4>{type === 'helmet' ? 'Authentic Speed' : asset.player}</h4><p>{type === 'helmet' ? 'Padrão · tamanho real · máscara à direita' : `Roster ${asset.associationSeason} · ${team} · GSIS ${asset.identifiers.gsis_id}`}</p><p className="media-credit">{asset.credit}</p><details><summary>Procedência e limites · {type === 'helmet' ? 'capacete' : 'retrato'}</summary><dl>
            <dt>Estado</dt><dd>Arquivo validado. Candidato não qualificado para publicação.</dd><dt>Arquivo original</dt><dd>{asset.width} × {asset.height} px · {asset.format} · {asset.transparency ? 'com transparência' : 'sem transparência'} · {(asset.bytes/1024).toFixed(0)} KiB</dd>
            <dt>Período visual</dt><dd>{asset.visualPeriod}</dd><dt>Origem</dt><dd><a href={asset.contextUrl}>Página de contexto</a> · <a href={asset.sourceUrl}>Arquivo na fonte</a></dd>
            <dt>Obtenção</dt><dd>{asset.obtainedAt}</dd><dt>Condições de uso</dt><dd>{asset.rights} <a href={asset.rightsEvidenceUrl}>Condições da fonte</a></dd><dt>Crédito exigido</dt><dd>{asset.requiredCredit}</dd><dt>Limitações</dt><dd>{asset.limitations.join(' ')}</dd><dt>SHA-256</dt><dd className="media-hash">{asset.sha256}</dd>
          </dl></details></figcaption>
        </figure>; })}
      </section>;
    })}</div>
    <section className="media-compare"><h2>Estudo da abertura do calendário</h2><p>Mesmo calendário e leituras reais dos participantes. O par de capacetes frente a frente está pendente; a abertura usa logos. Retratos permanecem nesta galeria.</p><div><Link className="journey-action" to={journeyHref(q,{view:null,game:null,entry:null,observation:null,season:'2026',week:'1',q:null,filter:'all',media:null})}>Abertura com logos</Link><Link className="journey-action" to={journeyHref(q,{view:null,game:null,entry:null,observation:null,season:'2026',week:'1',q:null,filter:'all',media:'helmets'})}>Estudo com capacetes</Link></div></section>
    <section className="media-recovery"><h2>Fallback e recuperação</h2><p>Imagem ausente, falha ou associação insuficiente mantém a identidade do time. A troca de time ou fonte permite nova tentativa.</p><div className="media-recovery-controls"><button aria-pressed={fallback} onClick={()=>setFallback(v=>!v)}>{fallback ? 'Restaurar candidato' : 'Simular mídia indisponível'}</button><button onClick={()=>setRetryTeam(t=>t==='BAL'?'IND':'BAL')}>Trocar para {retryTeam==='BAL'?'IND':'BAL'}</button></div><TeamMedia team={retryTeam} type="helmet" allowCandidate={!fallback}/></section>
  </div>;
}
