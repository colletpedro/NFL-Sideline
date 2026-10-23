import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import type { NflDataClient, PublicationContext } from '../src/services/dataClient';
import { StaticNflDataClient } from '../src/services/staticDataClient';
import type { Game, Team } from '../src/services/types';
import { Reading } from '../broadcast-real/Reading';
import { Logo } from '../broadcast-experience/TeamLogo';
import { teamIdentity } from '../broadcast-real/identity';
import { loadArchive, type Archive } from './sources';
import { dateLabel, gameState, relation, relationText, title } from './relations';
import { calendarChange, gameChange, journeyHref } from './state';
import { LiveReading } from './LiveReading';
import { nextReadingQuery } from './liveSelection';
import { readChoice } from './choice';
import { Discovery } from './Discovery';
import { MediaGallery } from './media/MediaGallery';
const calendar: NflDataClient = new StaticNflDataClient(window.fetch.bind(window));
const message = (e: unknown) => e instanceof Error ? e.message : 'Fonte indisponível.';
function Identity({ team, onSelect, selected }: { team: Team; onSelect?: (team: string) => void; selected?: boolean }) {
  const identity = teamIdentity(team.teamAbbr);
  const style = { '--team': identity.color, '--team-dark': identity.dark, '--optical': identity.optical } as CSSProperties;
  const content = <><Logo team={identity}/><div><span>{team.teamAbbr}{onSelect && (selected ? ' · Selecionado' : ' · Selecionar time')}</span><strong>{team.teamName}</strong></div></>;
  return onSelect ? <button type="button" className="journey-team" style={style} aria-pressed={selected} onClick={() => onSelect(team.teamAbbr)}>{content}</button> : <div className="journey-team" style={style}>{content}</div>;
}
function Band({ game, selectedTeam, onSelect }: { game: Game; selectedTeam?: string; onSelect?: (team: string) => void }) {
  const state = gameState(game);
  return <div className={`journey-band${onSelect ? ' journey-band-interactive' : ''}`} role={onSelect ? 'group' : undefined} aria-label={onSelect ? 'Escolha o time da leitura' : undefined}><Identity team={game.awayTeam} onSelect={onSelect} selected={selectedTeam === game.awayTeam.teamAbbr}/><Identity team={game.homeTeam} onSelect={onSelect} selected={selectedTeam === game.homeTeam.teamAbbr}/><div className="journey-score"><strong>{state.score ?? '×'}</strong><span>{state.label}</span></div></div>;
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
  const galleryRoute = q.get('view') === 'media';
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
  const week = q.has('week') ? Number(q.get('week')) : games ? 1 : null;
  const season = requestedSeason ?? String(publication?.defaultSeason ?? '');
  useEffect(() => {
    if (!games || !publication) return;
    if (!q.has('season') || !q.has('week')) {
      const next = new URLSearchParams(q); next.set('season', season); next.set('week', String(week ?? ''));
      setQ(next, { replace: true });
    }
  }, [games, publication, q, season, week, setQ]);
  useEffect(() => { heading.current?.focus(); window.scrollTo(0, 0); }, [gameId, galleryRoute]);
  const game = games?.find(g => g.gameId === gameId);
  const selected = archive?.documents.find(x => x.d.observationId === observationId && x.entry.entryId === entryId);
  const selectedRelation = game && selected ? relation(game, selected.d) : null;
  const calendarHref = journeyHref(q, { ...calendarChange, view: null }), matchupHref = journeyHref(q, gameChange);
  const choose = (change: Record<string, string>) => {
    if (game && archive) setQ(nextReadingQuery(game, archive, q, change));
    else if (game) setQ(new URLSearchParams(journeyHref(q, { ...change, entry: null, observation: null }).slice(2)));
  };
  const retryArchive = () => setArchiveRetry(v => v + 1);
  return <>
    <a href="#journey-main" className="skip-link">Ir ao conteúdo</a>
    <header className="site-header real-header"><div className="real-header-inner"><Link className="brand" to={calendarHref}>NFL <strong>SIDELINE</strong><i className="brand-rule"/></Link><nav aria-label="Navegação principal"><Link to={calendarHref}>Central do calendário</Link>{game && <Link to={matchupHref}>Confronto</Link>}</nav><p>Local · fontes preservadas<br/><span>Arquivo de leituras 2026 W1–2</span></p></div></header>
    <main id="journey-main" className="real-page journey-page">
      <nav className="journey-breadcrumb" aria-label="Caminho"><Link to={calendarHref}>Calendário · {season || 'arquivo'} · semana {week ?? '…'}</Link>{gameId && <><span>/</span><Link to={matchupHref}>{game ? `${game.awayTeam.teamAbbr} × ${game.homeTeam.teamAbbr}` : 'Confronto'}</Link></>}{readingRoute && <><span>/</span><span>Leitura do arquivo</span></>}</nav>
      <div className={`real-intro${readingRoute || gameId ? ' journey-reading-intro' : ''}`}><div><p>{readingRoute ? 'Uma observação por vez' : gameId ? 'Confronto identificado' : 'Jogos e leituras arquivadas'}</p><h1 ref={heading} tabIndex={-1}>{galleryRoute ? 'Acervo visual local.' : readingRoute ? 'O recorte, em seu contexto.' : game ? title(game) : gameId ? 'Confronto indisponível' : 'Encontre seu jogo.'}</h1></div></div>
      {galleryRoute && <nav className="media-local-nav"><Link to={calendarHref}>Voltar ao calendário</Link></nav>}
      {galleryRoute ? <MediaGallery q={q}/> : <>
      {calError && <section className="real-state" role="alert"><h2>Calendário indisponível.</h2><p>{calError} Nenhum jogo ou resultado foi substituído.</p><button onClick={() => { calendar.clearCache(); setCalRetry(v => v + 1); }}>Recarregar calendário</button></section>}
      {!games && !calError && <section className="real-state" role="status">Carregando calendário preservado…</section>}
      {(archiveError || !archive) && <section className="journey-source" role={archiveError ? 'alert' : 'status'}><h2>{archiveError ? 'Leituras indisponíveis nesta sessão.' : 'Conferindo a disponibilidade das leituras…'}</h2><p>{archiveError || 'Catálogo e documentos são conferidos na mesma sessão antes de anunciar relações.'}</p>{archiveError && <button onClick={retryArchive}>Recarregar arquivo de leituras</button>}</section>}
      {!gameId && !readingRoute && games && <Discovery games={games} archive={archive} archiveError={archiveError} q={q} season={season} week={week} onChange={setQ}/>}
      {gameId && games && !game && <section className="real-state" role="alert"><h2>Jogo não encontrado nesta temporada.</h2><p>A origem não pode ser validada; nenhuma associação foi concedida.</p><Link to={calendarHref}>Voltar ao calendário</Link></section>}
      {game && <>
        <Band game={game} selectedTeam={readChoice(game, q, selected?.d, archive).team} onSelect={team => choose({ team })}/><section className="journey-match-context journey-match-compact"><p>{dateLabel(game.gameday)} · {game.season} {game.gameType} · Semana {game.week}</p><details><summary>Sobre o jogo e o arquivo</summary><p>{game.gameId}</p><p>{game.homeTeam.teamName} como mandante. Estádio e horário não disponíveis neste arquivo.</p>{game.roof && <p>Cobertura: {game.roof}</p>}{game.surface && <p>Superfície: {game.surface}</p>}</details></section>
        {archive && <LiveReading game={game} archive={archive} q={q} memberLabels={Object.fromEntries((games ?? []).map(g => [g.gameId, title(g)]))} onChoice={choose} onQuery={next => setQ(next, { replace: true })}/>}
        <Link className="journey-back" to={calendarHref}>Voltar ao calendário · semana {week}</Link>
      </>}
      {readingRoute && !game && archive && <>
        {!selected ? <section className="real-state" role="alert"><h2>Observação não encontrada.</h2><p>Confira o arquivo e o recorte na URL. Nenhuma preferência anterior foi usada.</p><Link to={matchupHref}>Voltar ao confronto</Link></section> : <>
          <section className="journey-reading-context journey-relation-compact" aria-label="Relação com o confronto">
            <div><p>{'Origem do jogo não validada'}</p><strong role="status" aria-live="polite" data-relation={selectedRelation ?? 'unverified'}>{selectedRelation ? relationText(selectedRelation, selected.d) : 'Relação não conferida; calendário indisponível ou jogo não identificado'}</strong></div>
            <Link className="journey-secondary-action" to={matchupHref}>Voltar ao confronto</Link>
          </section>
          {selectedRelation === 'incompatible' ? <section className="real-state" role="alert"><h2>Esta observação não corresponde ao participante ou ao contexto do confronto.</h2><p>Abra uma leitura pelas opções do confronto. Nenhum vínculo válido foi atribuído.</p><Link to={matchupHref}>Escolher leitura no confronto</Link></section> : <Reading guided key={`${archive.catalog.sessionId}|${entryId}|${observationId}`} d={selected.d} entry={selected.entry} memberLabels={Object.fromEntries((games ?? []).map(g => [g.gameId, title(g)]))} detailsOpen={q.get('details') === 'open'} compositionOpen={q.get('composition') === 'open'} onDetailsChange={open => setQ(new URLSearchParams(journeyHref(q, { details: open ? 'open' : null }).slice(2)), { replace: true })} onCompositionChange={open => setQ(new URLSearchParams(journeyHref(q, { composition: open ? 'open' : null }).slice(2)), { replace: true })}/>}
          <Link className="journey-back" to={calendarHref}>Voltar ao calendário · semana {week}</Link>
        </>}
      </>}
      </>}
      {!galleryRoute && <details className="journey-publication"><summary>Acervo visual local</summary><Link className="journey-secondary-action" to={journeyHref(q,{view:'media'})}>Abrir galeria de mídia</Link></details>}
      <details className="journey-publication"><summary>Fontes e atualização do arquivo</summary><p>Calendário: {publication?.generatedAt ? `publicado em ${new Date(publication.generatedAt).toLocaleString('pt-BR', { timeZone: 'UTC' })} UTC` : calError ? 'indisponível' : 'carregando publicação…'}. Arquivo preservado, sem placar ao vivo.</p><p>Leituras: arquivo independente, com períodos e cobertura próprios. A publicação do calendário não data nem atualiza as métricas.</p></details>
    </main><footer className="real-footer"><span className="brand">NFL <strong>SIDELINE</strong></span><p>Futebol americano, sob outra perspectiva.</p><span>Experiência local · sem previsão ou comparação entre times</span></footer>
  </>;
}
