import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import type { NflDataClient, PublicationContext } from '../src/services/dataClient';
import { StaticNflDataClient } from '../src/services/staticDataClient';
import type { Game, Team } from '../src/services/types';
import { initialWeek } from '../src/services/calendar';
import { Reading } from '../broadcast-real/Reading';
import { Logo } from '../broadcast-experience/TeamLogo';
import { teamIdentity } from '../broadcast-real/identity';
import { period } from '../local-editorial/observations/selection';
import { loadArchive, type Archive } from './sources';
import { dateLabel, gameState, groups, relation, relationText, title, type Relation } from './relations';
import { calendarChange, gameChange, journeyHref } from './state';
const calendar: NflDataClient = new StaticNflDataClient(window.fetch.bind(window));
const message = (e: unknown) => e instanceof Error ? e.message : 'Fonte indisponível.';
const role = { off: 'Ataque', def: 'Defesa' }, foundation = { general: 'Passe + corrida', classified_pass: 'Passe', classified_rush: 'Corrida' };
function Identity({ team }: { team: Team }) {
  const identity = teamIdentity(team.teamAbbr);
  return <div className="journey-team" style={{ '--team': identity.color, '--team-dark': identity.dark, '--optical': identity.optical } as CSSProperties}><Logo team={identity}/><div><span>{team.teamAbbr}</span><strong>{team.teamName}</strong></div></div>;
}
function Band({ game }: { game: Game }) {
  const state = gameState(game);
  return <div className="journey-band"><Identity team={game.awayTeam}/><Identity team={game.homeTeam}/><div className="journey-score"><strong>{state.score ?? '×'}</strong><span>{state.label}</span></div></div>;
}
export default function App() {
  const [q, setQ] = useSearchParams();
  const [storedPublication, setPublication] = useState<PublicationContext | null>(null), [storedGames, setGames] = useState<Game[] | null>(null);
  const [storedArchive, setArchive] = useState<Archive | null>(null);
  const [calError, setCalError] = useState(''), [archiveError, setArchiveError] = useState('');
  const [calRetry, setCalRetry] = useState(0), [archiveRetry, setArchiveRetry] = useState(0);
  const requestedSeason = q.get('season');
  const calendarKey = `${requestedSeason}|${calRetry}`;
  const [loadedCalendarKey, setLoadedCalendarKey] = useState('');
  const [loadedArchiveRevision, setLoadedArchiveRevision] = useState(-1);
  const games = loadedCalendarKey === calendarKey ? storedGames : null;
  const publication = loadedCalendarKey === calendarKey ? storedPublication : null;
  const archive = loadedArchiveRevision === archiveRetry ? storedArchive : null;
  const heading = useRef<HTMLHeadingElement>(null);
  const gameId = q.get('game'), observationId = q.get('observation'), entryId = q.get('entry');
  const readingRoute = observationId !== null || entryId !== null;
  useEffect(() => {
    let active = true;
    setGames(null); setPublication(null); setCalError('');
    calendar.getPublicationContext().then(async publication => {
      const season = requestedSeason === null ? publication.defaultSeason : Number(requestedSeason);
      const games = await calendar.listGames(season);
      if (active) { setPublication(publication); setGames(games); setLoadedCalendarKey(calendarKey); }
    }).catch(e => { if (active) setCalError(message(e)); });
    return () => { active = false; };
  }, [requestedSeason, calRetry, calendarKey]);
  useEffect(() => {
    let active = true; const c = new AbortController();
    setArchive(null); setArchiveError('');
    loadArchive(c.signal).then(a => { if (active) { setArchive(a); setLoadedArchiveRevision(archiveRetry); } }).catch(e => { if (active) setArchiveError(message(e)); });
    return () => { active = false; c.abort(); };
  }, [archiveRetry]);
  const week = q.has('week') ? Number(q.get('week')) : games ? initialWeek(games, new Date()) : null;
  const season = requestedSeason ?? String(publication?.defaultSeason ?? '');
  useEffect(() => {
    if (!games || !publication) return;
    if (!q.has('season') || !q.has('week')) {
      const next = new URLSearchParams(q); next.set('season', season); next.set('week', String(week ?? ''));
      setQ(next, { replace: true });
    }
  }, [games, publication, q, season, week, setQ]);
  useEffect(() => { heading.current?.focus(); window.scrollTo(0, 0); }, [gameId, readingRoute]);
  const game = games?.find(g => g.gameId === gameId);
  const selected = archive?.documents.find(x => x.d.observationId === observationId && x.entry.entryId === entryId);
  const selectedRelation = game && selected ? relation(game, selected.d) : null;
  const calendarHref = journeyHref(q, calendarChange), matchupHref = journeyHref(q, gameChange);
  const ready = !!archive;
  const relevant = (g: Game) => archive?.documents.filter(x => [g.homeTeam.teamAbbr, g.awayTeam.teamAbbr].includes(x.d.subject.team)) ?? [];
  function availability(g: Game) {
    if (archiveError) return 'Arquivo de leituras indisponível';
    if (!archive) return 'Disponibilidade de leituras em conferência';
    const relations = relevant(g).map(x => relation(g, x.d));
    return relations.includes('individual') ? 'Leituras arquivadas deste jogo' : relations.includes('includes') ? 'Períodos arquivados incluem este jogo' : relations.includes('gap') ? 'Lacuna deste jogo; outros recortes no arquivo' : relations.includes('archive') || relations.includes('other') ? 'Outros recortes do participante no arquivo' : 'Nenhuma leitura dos participantes neste arquivo';
  }
  const weekGames = games?.filter(g => g.week === week) ?? [];
  const filtered = q.get('filter') === 'participants' ? weekGames.filter(g => ready && relevant(g).length > 0) : weekGames;
  const focus = filtered[0];
  const observationHref = (entry: string, observation: string) => journeyHref(q, { entry, observation, details: null, composition: null });
  const retryArchive = () => setArchiveRetry(v => v + 1);
  return <>
    <a href="#journey-main" className="skip-link">Ir ao conteúdo</a>
    <header className="site-header real-header"><div className="real-header-inner"><Link className="brand" to={calendarHref}>NFL <strong>SIDELINE</strong><i className="brand-rule"/></Link><nav aria-label="Navegação principal"><Link to={calendarHref}>Central do calendário</Link>{game && <Link to={matchupHref}>Confronto</Link>}</nav><p>Local · fontes preservadas<br/><span>Sem atualização ao vivo</span></p></div></header>
    <main id="journey-main" className="real-page journey-page">
      <nav className="journey-breadcrumb" aria-label="Caminho"><Link to={calendarHref}>Calendário · {season || 'arquivo'} · semana {week ?? '…'}</Link>{gameId && <><span>/</span><Link to={matchupHref}>{game ? `${game.awayTeam.teamAbbr} × ${game.homeTeam.teamAbbr}` : 'Confronto'}</Link></>}{readingRoute && <><span>/</span><span>Leitura do arquivo</span></>}</nav>
      <div className="real-intro"><div><p>{readingRoute ? 'Uma observação por vez' : gameId ? 'Confronto identificado' : 'Jogos e leituras arquivadas'}</p><h1 ref={heading} tabIndex={-1}>{readingRoute ? 'O recorte, em seu contexto.' : game ? title(game) : gameId ? 'Confronto indisponível' : 'Central do calendário'}</h1></div></div>
      <aside className="journey-publication"><p>Calendário: {publication?.generatedAt ? `publicado em ${new Date(publication.generatedAt).toLocaleString('pt-BR', { timeZone: 'UTC' })} UTC` : calError ? 'indisponível' : 'carregando publicação…'}. Arquivo preservado, sem placar ao vivo.</p><p>Leituras: arquivo independente, com períodos e cobertura próprios. A publicação do calendário não data nem atualiza as métricas.</p></aside>
      {calError && <section className="real-state" role="alert"><h2>Calendário indisponível.</h2><p>{calError} Nenhum jogo ou resultado foi substituído.</p><button onClick={() => { calendar.clearCache(); setCalRetry(v => v + 1); }}>Recarregar calendário</button></section>}
      {!games && !calError && <section className="real-state" role="status">Carregando calendário preservado…</section>}
      {(archiveError || !archive) && <section className="journey-source" role={archiveError ? 'alert' : 'status'}><h2>{archiveError ? 'Leituras indisponíveis nesta sessão.' : 'Conferindo a disponibilidade das leituras…'}</h2><p>{archiveError || 'Catálogo e documentos são conferidos na mesma sessão antes de anunciar relações.'}</p>{archiveError && <button onClick={retryArchive}>Recarregar arquivo de leituras</button>}</section>}
      {!gameId && !readingRoute && games && <>
        <section className="journey-controls" aria-label="Seleção do calendário">
          <label>Temporada disponível<select aria-label="Temporada disponível" value={season} onChange={e => setQ(new URLSearchParams({ season: e.target.value }))}><option value={publication!.defaultSeason}>{publication!.defaultSeason}</option></select></label>
          <label>Semana<select aria-label="Semana" value={week ?? ''} onChange={e => setQ(new URLSearchParams(journeyHref(q, { ...calendarChange, week: e.target.value }).slice(2)))}>{[...new Set(games.map(g => g.week))].map(w => <option key={w} value={w}>{w}</option>)}</select></label>
          <label>Exibir jogos<select aria-label="Exibir jogos" value={q.get('filter') ?? 'all'} onChange={e => setQ(new URLSearchParams(journeyHref(q, { filter: e.target.value }).slice(2)))}><option value="all">Todos os jogos</option><option value="participants">Com recortes dos participantes</option></select></label>
          <p>O filtro inclui arquivos de outros períodos, temporadas e lacunas. Não significa leitura exclusiva do jogo.</p>
        </section>
        {q.get('filter') === 'participants' && !ready ? <p role="status">O filtro aguarda a conferência do arquivo. Selecione “Todos os jogos” para explorar o calendário.</p> : <>
          <div className="journey-list-heading"><h2>Semana {week}</h2><span>{filtered.length} de {weekGames.length} jogos da semana</span></div>
          {focus && <section className="journey-feature"><Band game={focus}/><div><h2>{title(focus)}</h2><p>{dateLabel(focus.gameday)} · {availability(focus)}</p><Link className="journey-action" to={journeyHref(q, { game: focus.gameId })}>Explorar confronto</Link></div></section>}
          <ul className="journey-games">{filtered.map(g => <li key={g.gameId}><div className="journey-mini"><b>{g.awayTeam.teamAbbr}</b><span>×</span><b>{g.homeTeam.teamAbbr}</b></div><div><h3>{title(g)}</h3><p>{dateLabel(g.gameday)} · {gameState(g).label}</p><p>{availability(g)}</p>{gameState(g).score && <strong>{gameState(g).score}</strong>}</div><Link className="journey-action" aria-label={`Abrir confronto ${g.awayTeam.teamAbbr} ${g.homeTeam.teamAbbr}`} to={journeyHref(q, { game: g.gameId })}>Abrir confronto</Link></li>)}</ul>
          {!filtered.length && <section className="real-state"><h2>Nenhum jogo nesta seleção.</h2><p>Altere a semana ou volte a todos os jogos.</p><Link to={journeyHref(q, { filter: 'all' })}>Mostrar todos os jogos</Link></section>}
        </>}
      </>}
      {gameId && games && !game && <section className="real-state" role="alert"><h2>Jogo não encontrado nesta temporada.</h2><p>A origem não pode ser validada; nenhuma associação foi concedida.</p><Link to={calendarHref}>Voltar ao calendário</Link></section>}
      {game && !readingRoute && <>
        <Band game={game}/><section className="journey-match-context"><p>{dateLabel(game.gameday)} · {game.season} {game.gameType} · Semana {game.week}</p><p>Local: {game.homeTeam.teamName} como mandante. Estádio e horário não disponíveis neste arquivo.{game.roof && ` Cobertura: ${game.roof}.`}{game.surface && ` Superfície: ${game.surface}.`}</p><details><summary>Identificação do jogo</summary><p>{game.gameId}</p></details><Link className="journey-action" to={calendarHref}>Voltar ao calendário · semana {week}</Link></section>
        <div className="journey-list-heading"><h2>O que o arquivo permite abrir</h2></div><p className="journey-explain">Cada leitura descreve um time e um período próprio. Abrir arquivos dos dois participantes não constitui comparação. Nenhum recorte demonstra conhecimento anterior ao kickoff.</p>
        {archive && <>
          {([game.awayTeam, game.homeTeam]).map(t => !relevant(game).some(x => x.d.subject.team === t.teamAbbr) && <p className="journey-empty" key={t.teamAbbr}>{t.teamName}: nenhuma leitura disponível neste arquivo.</p>)}
          {(Object.keys(groups) as Exclude<Relation, 'incompatible'>[]).map(group => {
            const items = relevant(game).filter(x => relation(game, x.d) === group);
            return <section className="journey-relations" key={group} aria-label={groups[group]}><h2>{groups[group]}</h2><p>{group === 'archive' ? 'Seleção explícita abre o arquivo com temporada e fase destacadas. Não preenche lacunas do confronto.' : group === 'other' ? 'Recortes próprios do participante; não são estatísticas exclusivas desta partida.' : group === 'gap' ? 'Ausência de fonte permanece visível e nunca é substituída por outra semana.' : group === 'individual' ? 'Amostra de um único jogo identificado. Completude e conhecimento temporal não certificados.' : 'Amostras de vários jogos; os números não são exclusivos desta partida.'}</p>
              {!items.length ? <p className="journey-empty">Nenhuma observação nesta categoria.</p> : <ul>{items.map(({ d, entry }) => <li key={entry.entryId + d.observationId}><div><h3>{d.subject.team} · {role[d.subject.role]} · {foundation[d.subject.foundation]}</h3><p>{period(d)}</p><p>{relationText(group, d)}</p></div><Link className="journey-action" to={observationHref(entry.entryId, d.observationId)}>Abrir {group === 'gap' ? 'lacuna' : group === 'archive' ? 'arquivo separado' : 'leitura'}</Link></li>)}</ul>}
            </section>;
          })}
        </>}
      </>}
      {readingRoute && archive && <>
        {!selected ? <section className="real-state" role="alert"><h2>Observação não encontrada.</h2><p>Confira o arquivo e o recorte na URL. Nenhuma preferência anterior foi usada.</p><Link to={matchupHref}>Voltar ao confronto</Link></section> : <>
          <section className="journey-reading-context" aria-label="Relação com o confronto"><h2>{game ? `Origem: ${title(game)}` : 'Origem do jogo não validada'}</h2><p>{game ? `${game.season} ${game.gameType} · Semana ${game.week} · ${dateLabel(game.gameday)}` : 'O calendário precisa estar disponível e identificar o jogo para conferir o vínculo.'}</p><strong role="status" aria-live="polite" data-relation={selectedRelation ?? 'unverified'}>{selectedRelation ? relationText(selectedRelation, selected.d) : 'Relação não conferida'}</strong><p>Período da observação: {period(selected.d)}</p><Link className="journey-action" to={matchupHref}>Voltar ao confronto</Link><Link className="journey-back" to={calendarHref}>Voltar ao calendário · semana {week}</Link></section>
          <section className="real-selection"><div className="real-selection-bar"><label className="journey-observation-label">Explorar outro recorte do arquivo<select aria-label="Recorte do arquivo" value={`${entryId}|${observationId}`} onChange={e => { const [entry, observation] = e.target.value.split('|'); setQ(new URLSearchParams(observationHref(entry, observation).slice(2))); }}>{archive.documents.map(({ d, entry }) => <option key={entry.entryId + d.observationId} value={`${entry.entryId}|${d.observationId}`}>{d.subject.team} · {role[d.subject.role]} · {foundation[d.subject.foundation]} · {period(d)}</option>)}</select></label></div><p className="real-notice">A troca abre somente combinações existentes. A relação com o jogo é conferida novamente a cada seleção.</p></section>
          {selectedRelation === 'incompatible' ? <section className="real-state" role="alert"><h2>Esta observação não corresponde ao participante ou ao contexto do confronto.</h2><p>Abra uma leitura pelas opções do confronto. Nenhum vínculo válido foi atribuído.</p><Link to={matchupHref}>Escolher leitura no confronto</Link></section> : <Reading key={`${archive.catalog.sessionId}|${entryId}|${observationId}`} d={selected.d} entry={selected.entry} memberLabels={Object.fromEntries((games ?? []).map(g => [g.gameId, title(g)]))} detailsOpen={q.get('details') === 'open'} compositionOpen={q.get('composition') === 'open'} onDetailsChange={open => setQ(new URLSearchParams(journeyHref(q, { details: open ? 'open' : null }).slice(2)), { replace: true })} onCompositionChange={open => setQ(new URLSearchParams(journeyHref(q, { composition: open ? 'open' : null }).slice(2)), { replace: true })}/>}
        </>}
      </>}
    </main><footer className="real-footer"><span className="brand">NFL <strong>SIDELINE</strong></span><p>Futebol americano, sob outra perspectiva.</p><span>Experiência local · sem previsão ou comparação entre times</span></footer>
  </>;
}
