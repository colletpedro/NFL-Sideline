import { useId, useRef } from 'react';
import { axisMagnitude, coordinate, signedDomain } from './decimal';
import type { Encounter, Evidence, Finding, VisualAnalysisDocument } from './model';
import './visual.css';

const foundation = { PASS: 'Passe', RUSH: 'Corrida', GENERAL: 'Panorama geral' } as const;
const absent = {
  MISSING_ATTACK: 'Sem observações do ataque neste fundamento.',
  MISSING_DEFENSE: 'Sem observações da defesa neste fundamento.',
  MISSING_BOTH: 'Sem observações de ataque e defesa neste fundamento.',
  INCOMPATIBLE_ORIGIN: 'Séries de origens diferentes; não há comparação entre elas.',
} as const;
const relation = {
  ADDITIONAL_RESTRICTION: 'Limitação adicional',
  INDEPENDENT_OPPORTUNITY: 'Oportunidade independente',
} as const;
const period = (rows: Evidence[]) => rows.length ?
  `${rows[0].origin === 'HISTORICAL_REFERENCE' ? 'Referência histórica' : 'Temporada atual'} · ${rows[0].season} · semanas ${rows.map(row => row.week).join(', ')}` :
  'Sem semanas observadas';

function Coverage({ rows, expected }: { rows: Evidence[]; expected: number[] }) {
  if (!rows.length) return null;
  if (rows[0].origin === 'HISTORICAL_REFERENCE')
    return <p className="visual-coverage">Referência histórica; semanas esperadas da temporada atual não se aplicam.</p>;
  const observed = new Set(rows.map(row => row.week));
  const missing = expected.filter(week => !observed.has(week));
  return <p className="visual-coverage">Cobertura: {expected.length - missing.length}/{expected.length} semanas esperadas.
    {missing.length > 0 && ` Sem observação em S${missing.join(', S')}; motivo não identificado.`}</p>;
}

function seriesRows(document: VisualAnalysisDocument, id: string | null): Evidence[] {
  const series = document.series.find(item => item.id === id);
  return (series?.evidenceIds ?? []).map(key => document.evidence.find(item => item.id === key)!);
}

function SeriesPlot({ label, rows, maximum, role, expected, sharedPeriod }: { label: string; rows: Evidence[]; maximum: string; role: 'attack' | 'defense'; expected: number[]; sharedPeriod: boolean }) {
  return <div className={`visual-series visual-series-${role}`}>
    <h4><span aria-hidden="true">{role === 'attack' ? '●' : '◆'}</span> {label}</h4>
    <p className="visual-period">{!sharedPeriod && `${period(rows)} · `}{!rows.length || rows.some(row => row.plays === null) ? 'volume de jogadas não informado' : `${rows.reduce((sum, row) => sum + (row.plays ?? 0), 0)} jogadas observadas`}</p>
    <Coverage rows={rows} expected={expected}/>
    {rows.length === 0 ? <p className="visual-absent">Sem observações nesta série.</p> : <div className="visual-plot" role="img" aria-label={`${label}: ${rows.map(row => `semana ${row.week}, ${row.displayValue} EPA por jogada`).join('; ')}`}>
      <div className="visual-axis-labels"><span>≈ −{axisMagnitude(maximum)}</span><span>zero</span><span>≈ +{axisMagnitude(maximum)}</span></div>
      {rows.map(row => {
        const x = coordinate(row.value, maximum);
        return <div className="visual-point-row" key={row.id}>
          <span className="visual-week">S{row.week}</span>
          <span className="visual-track" aria-hidden="true"><span className="visual-zero"/>
            {x !== null && <span className={`visual-point visual-point-${role}`} style={{ left: `${x}%` }}/>}</span>
          <strong className="visual-value">{row.displayValue}</strong>
        </div>;
      })}
      {rows.some(row => coordinate(row.value, maximum) === null) && <p className="visual-coordinate-note">Ponto fora da precisão do desenho; consulte o valor exato e a tabela.</p>}
    </div>}
  </div>;
}

function EvidenceTable({ attack, defense, attackTeam, defenseTeam, base }: { attack: Evidence[]; defense: Evidence[]; attackTeam: string; defenseTeam: string; base: string }) {
  const tableId = useId();
  return <details className="visual-details"><summary>Tabela de evidências e definição</summary>
    <p>EPA por jogada no fundamento indicado (passe, corrida ou panorama geral), no recorte semanal. Na defesa, EPA permitido menor é melhor. Os valores são semanais; não há média nova de período ou ajuste por adversário. Volume “não informado” não equivale a zero.</p>
    {attack.length || defense.length ? <><p className="visual-table-hint">Em telas estreitas, foque a tabela e use as setas para rolar.</p><div className="visual-table-wrap" tabIndex={0} role="region" aria-labelledby={tableId}><table>
      <caption id={tableId}>{base} · Observações semanais de {attackTeam} no ataque e {defenseTeam} na defesa</caption>
      <thead><tr><th scope="col">Papel</th><th scope="col">Time</th><th scope="col">Período</th><th scope="col">EPA por jogada</th><th scope="col">Valor exato</th><th scope="col">Jogadas</th></tr></thead>
      <tbody>{[...attack.map(row => ({ row, label: 'Ataque' })), ...defense.map(row => ({ row, label: 'Defesa · EPA permitido' }))].map(({ row, label }) => <tr key={row.id}>
        <th scope="row">{label}</th><td>{row.team}</td><td>{row.season} · S{row.week}{row.origin === 'HISTORICAL_REFERENCE' ? ' · histórico' : ''}</td>
        <td>{row.displayValue}</td><td><code>{row.value}</code></td><td>{row.plays ?? 'Não informado'}</td>
      </tr>)}</tbody>
    </table></div></> : <p>Nenhuma observação disponível neste encontro.</p>}
  </details>;
}

function EncounterCard({ document, encounter, maximum, compact = false, cardRef }: {
  document: VisualAnalysisDocument; encounter: Encounter; maximum: string | null; compact?: boolean; cardRef: (node: HTMLElement | null) => void;
}) {
  const attack = seriesRows(document, encounter.attackSeriesId), defense = seriesRows(document, encounter.defenseSeriesId);
  const sharedPeriod = attack.length > 0 && defense.length > 0 && period(attack) === period(defense);
  const finding = document.findings.find(item => item.encounterId === encounter.id);
  const restriction = finding && document.restrictions.find(item => item.id === finding.primaryRestrictionId);
  const highlighted = finding && document.presentation.highlightFindingIds.includes(finding.id);
  const related = finding && document.links.filter(link => link.fromFindingId === finding.id || link.toFindingId === finding.id);
  return <article ref={cardRef} tabIndex={-1} aria-label={`${encounter.attackTeam} ataque × ${encounter.defenseTeam} defesa · ${foundation[encounter.foundation]}`} className={`visual-card${highlighted ? ' visual-card-highlight' : ''}${compact ? ' visual-card-general' : ''}`}>
    <header className="visual-card-head"><div><p className="visual-kicker">{encounter.attackTeam} ataque × {encounter.defenseTeam} defesa</p>
      <h3>{foundation[encounter.foundation]}</h3></div><span className="visual-state">{highlighted ? 'Destaque' : encounter.state === 'UNAVAILABLE' ? 'Evidência ausente' : encounter.state === 'REPRESENTED_BY' ? 'Agrupado' : 'Achado'}</span></header>
    {finding ? <div className="visual-finding"><h4>{finding.title}</h4><p>{finding.summary}</p></div> :
      encounter.state === 'REPRESENTED_BY' ? <p className="visual-finding">Panorama agrupado com o encontro de {encounter.representedByFindingIds.map(id => {
        const source: Finding | undefined = document.findings.find(item => item.id === id);
        const target = document.encounters.find(item => item.id === source?.encounterId);
        return target ? foundation[target.foundation].toLowerCase() : 'fundamento';
      }).join(' e ')}. Os números abaixo permanecem próprios deste panorama.</p> :
      <p className="visual-finding visual-absent">{absent[encounter.unavailableReason ?? 'MISSING_BOTH']} Ausência não é zero.</p>}
    {restriction && <p className="visual-restriction"><strong>Limitação principal</strong> {restriction.text}</p>}
    {sharedPeriod && <p className="visual-shared-period">Ataque e defesa: {period(attack)}</p>}
    {maximum && <div className="visual-series-grid">
      <SeriesPlot label={`${encounter.attackTeam} · ataque`} rows={attack} maximum={maximum} role="attack" expected={document.scope.expectedCurrentWeeks} sharedPeriod={sharedPeriod}/>
      <SeriesPlot label={`${encounter.defenseTeam} · defesa (EPA permitido)`} rows={defense} maximum={maximum} role="defense" expected={document.scope.expectedCurrentWeeks} sharedPeriod={sharedPeriod}/>
    </div>}
    {related && related.length > 0 && <div className="visual-related"><strong>Relações com outros achados</strong><ul>{related.map((link, index) => {
      const other = document.findings.find(item => item.id === (link.fromFindingId === finding?.id ? link.toFindingId : link.fromFindingId));
      const target = document.encounters.find(item => item.id === other?.encounterId);
      return <li key={`${index}-${link.fromFindingId}`}>{relation[link.relation]}: {target?.attackTeam} · {target && foundation[target.foundation].toLowerCase()}</li>;
    })}</ul></div>}
    <EvidenceTable attack={attack} defense={defense} attackTeam={encounter.attackTeam} defenseTeam={encounter.defenseTeam} base={foundation[encounter.foundation]}/>
  </article>;
}

export function VisualAnalysis({ document }: { document: VisualAnalysisDocument }) {
  const cardRefs = useRef(new Map<string, HTMLElement>());
  const openEncounter = (id: string) => {
    const card = cardRefs.current.get(id);
    const details = card?.closest('details');
    if (details) details.open = true;
    card?.focus();
  };
  const keepRef = (id: string) => (node: HTMLElement | null) => {
    if (node) cardRefs.current.set(id, node); else cardRefs.current.delete(id);
  };
  const maximum = signedDomain(document.evidence.map(row => row.value));
  const cards = [document.game.awayTeam, document.game.homeTeam].flatMap(team => (['PASS', 'RUSH'] as const).map(base =>
    document.encounters.find(item => item.attackTeam === team && item.foundation === base)!));
  const general = [document.game.awayTeam, document.game.homeTeam].map(team => document.encounters.find(item => item.attackTeam === team && item.foundation === 'GENERAL')!);
  const highlights = document.presentation.highlightFindingIds.map(id => document.findings.find(item => item.id === id)!);
  return <section className="visual-analysis" aria-labelledby="visual-title">
    <div className="visual-intro"><div><p className="visual-kicker">LEITURA VISUAL · {document.game.season} · SEMANA {document.game.week}</p><h2 id="visual-title">Quatro encontros do confronto</h2>
      <p>Indicadores semanais de ataque e EPA permitido pela defesa. O eixo é assinado e usa a mesma escala em todos os encontros desta análise.</p></div>
      <span className="visual-local-tag">{document.source.kind === 'CONTRACT_FIXTURE' ? 'FIXTURE SINTÉTICA · NÃO GERADA' : 'RESULTADO LOCAL · NÃO PUBLICADO'}</span></div>
    <div className="visual-highlights"><h3>Leitura rápida</h3>{highlights.length ? <><p>{highlights.length > 1 ? 'Destaques equivalentes; nenhum deles desempata o confronto.' : 'Destaque editorial do recorte.'}</p>
      <ul>{highlights.map(item => {
        const encounter = document.encounters.find(e => e.id === item.encounterId)!;
        const restriction = document.restrictions.find(r => r.id === item.primaryRestrictionId)!;
        const attackPeriod = period(seriesRows(document, encounter.attackSeriesId));
        const defensePeriod = period(seriesRows(document, encounter.defenseSeriesId));
        return <li key={item.id}><button type="button" onClick={() => openEncounter(encounter.id)}>
          <strong>{encounter.attackTeam} ataque × {encounter.defenseTeam} defesa · {foundation[encounter.foundation]}</strong>
          <span>{item.title}</span><small>Limitação: {restriction.text}</small>
          {attackPeriod === defensePeriod ? <small>Ataque e defesa: {attackPeriod}</small> : <><small>Ataque: {attackPeriod}</small><small>Defesa: {defensePeriod}</small></>}
          <span className="visual-jump">Ver encontro e evidências ↓</span>
        </button></li>;
      })}</ul></> : <p>Não há achado destacado neste recorte. Consulte cada encontro e suas observações disponíveis.</p>}<p className="visual-no-winner">{document.restrictions.find(item => item.code === 'NO_OPPONENT_ADJUSTMENT')?.text} A cor lima identifica destaques; a quantidade de cartões não é um placar.</p></div>
    <div className="visual-legend" aria-label="Legenda do gráfico"><span><i className="visual-legend-attack"/> Ataque · EPA produzido</span><span><i className="visual-legend-defense"/> Defesa · EPA permitido</span><span>Esquerda: negativo · centro: zero · direita: positivo</span><span>Ataque: maior EPA é melhor · Defesa: menor EPA permitido é melhor</span><span>Eixo em EPA por jogada · ≈ indica rótulo arredondado</span></div>
    <div className="visual-card-grid">{cards.map(item => <EncounterCard key={item.id} document={document} encounter={item} maximum={maximum} cardRef={keepRef(item.id)}/>)}</div>
    <details className="visual-general"><summary>Panoramas gerais · passe e corrida juntos</summary><p>Recortes adicionais acessíveis. “Agrupado” preserva o encontro e suas observações sem afirmar que seus valores sejam iguais aos de passe ou corrida.</p>
      <div className="visual-card-grid">{general.map(item => <EncounterCard key={item.id} document={document} encounter={item} maximum={maximum} compact cardRef={keepRef(item.id)}/>)}</div></details>
    <section className="visual-method"><h3>Limites do documento</h3><ul>{document.presentation.globalRestrictionIds.filter(id => document.restrictions.find(item => item.id === id)?.code !== 'NO_OPPONENT_ADJUSTMENT').map(id => {
      const item = document.restrictions.find(r => r.id === id)!;
      return <li key={id}>{item.text}</li>;
    })}</ul><p>Corte informado pela origem: {document.scope.declaredAsOfDate ?? 'não informado'}.</p></section>
  </section>;
}
