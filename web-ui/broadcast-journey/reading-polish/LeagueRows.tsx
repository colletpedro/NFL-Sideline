import {compareObservedRates} from './rates';
import {Logo} from '../../broadcast-experience/TeamLogo';
import {teamIdentity} from '../../broadcast-real/identity';
import {coordinate,permitted,rate,type Family,type Reference} from '../w12/model';
export function LeagueRows({reference:r,family}:{reference:Reference;family:Family}) {
 const points=r.teamRateDistribution.points;
 if(!permitted(r.permission,'leagueReference',points.map(p=>p.observationId)))return <p className="mr-unavailable">Referência da liga indisponível para esta operação.</p>;
 const title=`${family==='third'?'Conversões de terceira':'TDs em campanhas de red zone'} — ataques na W${r.weeks[0]}`;
 return <div className="mr-league rp-league" role="group" aria-label={`Referência da liga, ${family==='third'?'terceiras':'red zone'}`}><h3>{title}</h3>
 <p className="mr-note">{r.season} {r.phase} · {points.length} times com taxa, de {r.candidateTeams.length} candidatos. Cada linha é a produção ofensiva de um time nesta semana: {family==='third'?'conversões / tentativas elegíveis':'TDs ofensivos / campanhas que entraram nas 20'}.</p>
 <p className="rp-league-key"><span aria-hidden="true"/> {r.participantsIncluded.join(' e ')}: participantes deste confronto. Ordem pela taxa observada, com empates preservados no eixo.</p>
 <div className="rp-league-axis" aria-hidden="true"><span>Time</span><div><i>0%</i><i className="rp-quarter">25%</i><i>50%</i><i className="rp-quarter">75%</i><i>100%</i></div><span>Taxa · razão</span></div>
 <ul className="rp-league-rows" aria-label={`${title}; eixo horizontal de 0% a 100%`}>{[...points].sort(compareObservedRates).map(p=><li key={p.team} data-league-row={p.team} className={r.participantsIncluded.includes(p.team)?'rp-league-participant':''}>
 <span className="rp-league-team"><Logo team={{...teamIdentity(p.team),logoPlate:false}}/><strong>{p.team}</strong>{r.participantsIncluded.includes(p.team)&&<span className="rp-sr-only">, neste confronto</span>}</span>
 <span className="rp-league-track" aria-hidden="true"><span data-league-point={p.team} data-rate-x={coordinate(p)*1000} style={{left:`${coordinate(p)*100}%`}}/></span>
 <span className="rp-league-value"><strong>{rate(p)}</strong><span>{p.numerator}/{p.denominator}</span></span></li>)}</ul>
 {r.teamsWithoutRate.length>0&&<p className="mr-note rp-without-rate">Fora da escala, sem taxa: {r.teamsWithoutRate.map(p=>`${p.team} — ${p.status==='NO_OPPORTUNITIES'?'fonte presente, sem oportunidades elegíveis (0/0)':p.status==='INSUFFICIENT'?'registros insuficientes':'fonte ausente'}`).join('; ')}.</p>}
 <p className="mr-note">Taxa conjunta da amostra: {r.pooledRate.numerator}/{r.pooledRate.denominator} ({rate(r.pooledRate)}), calculada pelas somas, sem média das taxas dos times.</p>
 <p className="mr-note">{r.participantsIncluded.join(' e ')} pertencem à referência; estas produções não são uma amostra independente. Registros observados, sem ajuste ou inferência de qualidade.</p></div>;
}
