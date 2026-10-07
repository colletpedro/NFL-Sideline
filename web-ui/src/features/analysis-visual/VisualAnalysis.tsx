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

function SeriesPlot({ label, rows, maximum, role, expected }: { label: string; rows: Evidence[]; maximum: string; role: 'attack' | 'defense'; expected: number[] }) {
  return <div className={`visual-series visual-series-${role}`}>
    <h4>{role === 'attack' ? '●' : '◆'} {label}</h4>
    <p className="visual-period">{period(rows)} · {rows.length} {rows.length === 1 ? 'semana' : 'semanas'} · {!rows.length || rows.some(row => row.plays === null) ? 'volume de jogadas não informado' : `${rows.reduce((sum, row) => sum + (row.plays ?? 0), 0)} jogadas observadas`}</p>
    <Coverage rows={rows} expected={expected}/>
    {rows.length === 0 ? <p className="visual-absent">Sem observações nesta série.</p> : <div className="visual-plot" role="img" aria-label={`${label}: ${rows.map(row => `semana ${row.week}, ${row.displayValue} EPA por jogada`).join('; ')}`}>
      <div className="visual-axis-labels"><span>≈ −{axisMagnitude(maximum)}</span><span>zero</span><span>≈ +{axisMagnitude(maximum)}</span></div>
      {rows.map(row => {
        const x = coordinate(row.value, maximum);
        return <div className="visual-point-row" key={row.id}>
          <span className="visual-week">S{row.week} <small>{row.season}</small></span>
          <span className="visual-track" aria-hidden="true"><span className="visual-zero"/>
            {x !== null && <span className={`visual-point visual-point-${role}`} style={{ left: `${x}%` }}/>}</span>
          <strong className="visual-value">{row.displayValue}</strong>
        </div>;
      })}
      {rows.some(row => coordinate(row.value, maximum) === null) && <p className="visual-coordinate-note">Ponto fora da precisão do desenho; consulte o valor exato e a tabela.</p>}
    </div>}
  </div>;
}

function EvidenceTable({ attack, defense, attackTeam, defenseTeam }: { attack: Evidence[]; defense: Evidence[]; attackTeam: string; defenseTeam: string }) {
  return <details className="visual-details"><summary>Tabela de evidências e definição</summary>
    <p>EPA por jogada no fundamento indicado (passe, corrida ou panorama geral), no recorte semanal. Na defesa, EPA permitido menor é melhor. Os valores são semanais; não há média nova de período ou ajuste por adversário. Volume “não informado” não equivale a zero.</p>
    {attack.length || defense.length ? <div className="visual-table-wrap"><table>
      <caption>Observações semanais de {attackTeam} no ataque e {defenseTeam} na defesa</caption>
      <thead><tr><th scope="col">Papel</th><th scope="col">Time</th><th scope="col">Período</th><th scope="col">EPA por jogada</th><th scope="col">Valor exato</th><th scope="col">Jogadas</th></tr></thead>
      <tbody>{[...attack.map(row => ({ row, label: 'Ataque' })), ...defense.map(row => ({ row, label: 'Defesa · EPA permitido' }))].map(({ row, label }) => <tr key={row.id}>
        <th scope="row">{label}</th><td>{row.team}</td><td>{row.season} · S{row.week}{row.origin === 'HISTORICAL_REFERENCE' ? ' · histórico' : ''}</td>
        <td>{row.displayValue}</td><td><code>{row.value}</code></td><td>{row.plays ?? 'Não informado'}</td>
      </tr>)}</tbody>
    </table></div> : <p>Nenhuma observação disponível neste encontro.</p>}
  </details>;
}

function EncounterCard({ document, encounter, maximum, compact = false }: {
  document: VisualAnalysisDocument; encounter: Encounter; maximum: string | null; compact?: boolean;
}) {
  const series = new Map(document.series.map(item => [item.id, item]));
  const evidence = new Map(document.evidence.map(item => [item.id, item]));
  const getRows = (id: string | null) => id ? (series.get(id)?.evidenceIds ?? []).map(key => evidence.get(key)!) : [];
  const attack = getRows(encounter.attackSeriesId), defense = getRows(encounter.defenseSeriesId);
  const finding = document.findings.find(item => item.encounterId === encounter.id);
  const restriction = finding && document.restrictions.find(item => item.id === finding.primaryRestrictionId);
  const highlighted = finding && document.presentation.highlightFindingIds.includes(finding.id);
  const related = finding && document.links.filter(link => link.fromFindingId === finding.id || link.toFindingId === finding.id);
  return <article className={`visual-card${highlighted ? ' visual-card-highlight' : ''}${compact ? ' visual-card-general' : ''}`}>
    <header className="visual-card-head"><div><p className="visual-kicker">{encounter.attackTeam} ataque × {encounter.defenseTeam} defesa</p>
      <h3>{foundation[encounter.foundation]}</h3></div><span className="visual-state">{highlighted ? 'Destaque' : encounter.state === 'UNAVAILABLE' ? 'Evidência ausente' : encounter.state === 'REPRESENTED_BY' ? 'Agrupado' : 'Achado'}</span></header>
    {finding ? <div className="visual-finding"><h4>{finding.title}</h4><p>{finding.summary}</p></div> :
      encounter.state === 'REPRESENTED_BY' ? <p className="visual-finding">Panorama agrupado com o encontro de {encounter.representedByFindingIds.map(id => {
        const source: Finding | undefined = document.findings.find(item => item.id === id);
        const target = document.encounters.find(item => item.id === source?.encounterId);
        return target ? foundation[target.foundation].toLowerCase() : 'fundamento';
      }).join(' e ')}. Os números abaixo permanecem próprios deste panorama.</p> :
      <p className="visual-finding visual-absent">{absent[encounter.unavailableReason ?? 'MISSING_BOTH']} Ausência não é zero.</p>}
    {maximum && <div className="visual-series-grid">
      <SeriesPlot label={`${encounter.attackTeam} · ataque`} rows={attack} maximum={maximum} role="attack" expected={document.scope.expectedCurrentWeeks}/>
      <SeriesPlot label={`${encounter.defenseTeam} · defesa (EPA permitido)`} rows={defense} maximum={maximum} role="defense" expected={document.scope.expectedCurrentWeeks}/>
    </div>}
    {restriction && <p className="visual-restriction"><strong>Limitação principal</strong> {restriction.text}</p>}
    {related && related.length > 0 && <div className="visual-related"><strong>Relações com outros achados</strong><ul>{related.map((link, index) => {
      const other = document.findings.find(item => item.id === (link.fromFindingId === finding?.id ? link.toFindingId : link.fromFindingId));
      const target = document.encounters.find(item => item.id === other?.encounterId);
      return <li key={`${index}-${link.fromFindingId}`}>{relation[link.relation]}: {target?.attackTeam} · {target && foundation[target.foundation].toLowerCase()}</li>;
    })}</ul></div>}
    <EvidenceTable attack={attack} defense={defense} attackTeam={encounter.attackTeam} defenseTeam={encounter.defenseTeam}/>
  </article>;
}

export function VisualAnalysis({ document }: { document: VisualAnalysisDocument }) {
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
        return <li key={item.id}><strong>{encounter.attackTeam} · {foundation[encounter.foundation]}</strong><span>{item.title}</span><small>{restriction.text}</small></li>;
      })}</ul></> : <p>Não há achado destacado neste recorte. Consulte cada encontro e suas observações disponíveis.</p>}</div>
    <div className="visual-legend" aria-label="Legenda do gráfico"><span><i className="visual-legend-attack"/> Ataque · EPA produzido</span><span><i className="visual-legend-defense"/> Defesa · EPA permitido</span><span>Esquerda: negativo · centro: zero · direita: positivo</span><span>Ataque: maior EPA é melhor · Defesa: menor EPA permitido é melhor</span><span>Eixo em EPA por jogada · ≈ indica rótulo arredondado</span></div>
    <div className="visual-card-grid">{cards.map(item => <EncounterCard key={item.id} document={document} encounter={item} maximum={maximum}/>)}</div>
    <details className="visual-general"><summary>Panoramas gerais · passe e corrida juntos</summary><p>Recortes adicionais acessíveis. “Agrupado” preserva o encontro e suas observações sem afirmar que seus valores sejam iguais aos de passe ou corrida.</p>
      <div className="visual-card-grid">{general.map(item => <EncounterCard key={item.id} document={document} encounter={item} maximum={maximum} compact/>)}</div></details>
    <section className="visual-method"><h3>Limites do documento</h3><ul>{document.presentation.globalRestrictionIds.map(id => {
      const item = document.restrictions.find(r => r.id === id)!;
      return <li key={id}>{item.text}</li>;
    })}</ul><p>O corte informado é {document.scope.declaredAsOfDate ?? 'não informado'}. A garantia temporal cobre a ordem das semanas, não a disponibilidade histórica em cada data.</p></section>
  </section>;
}
