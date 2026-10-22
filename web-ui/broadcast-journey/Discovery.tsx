import { useEffect, useRef, useState, type CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import type { Game, Team } from '../src/services/types';
import { Logo } from '../broadcast-experience/TeamLogo';
import { teamIdentity } from '../broadcast-real/identity';
import type { Archive } from './sources';
import { calendarChange, journeyHref } from './state';
import { dateLabel, gameState, title } from './relations';
import { availabilityAction, availabilityDescription, availabilityTeams, gameAvailability, searchGames, selectGames } from './discoveryModel';

type Props = { games: Game[]; archive: Archive | null; archiveError: string; q: URLSearchParams; season: string; week: number | null; onChange: (q: URLSearchParams) => void };
function Participant({ team, large = false }: { team: Team; large?: boolean }) {
  const visual = teamIdentity(team.teamAbbr);
  return <div className={`discovery-team${large ? ' discovery-team-large' : ''}`} style={{ '--team': visual.color, '--team-dark': visual.dark, '--optical': visual.optical } as CSSProperties}>
    <Logo team={visual}/><div>{large ? <><span>{visual.city} · {team.teamAbbr}</span><strong>{visual.name}</strong></> : <><strong>{team.teamName}</strong><span>{team.teamAbbr}</span></>}</div>
  </div>;
}
export function Discovery({ games, archive, archiveError, q, season, week, onChange }: Props) {
  const query = q.get('q') ?? '', scope = q.get('scope') === 'season' ? 'season' : 'week';
  const [draft, setDraft] = useState(query), searchInput = useRef<HTMLInputElement>(null), resultsHeading = useRef<HTMLHeadingElement>(null);
  useEffect(() => setDraft(query), [query]);
  const weekGames = games.filter(g => g.week === week);
  const participantsOnly = q.get('filter') === 'participants';
  const inFilter = (g: Game) => !participantsOnly || !!archive?.documents.some(({ d }) => [g.homeTeam.teamAbbr, g.awayTeam.teamAbbr].includes(d.subject.team));
  const filtered = weekGames.filter(inFilter), searching = query.trim().length > 0;
  const matches = searchGames((scope === 'season' ? games : weekGames).filter(inFilter), query);
  const pageSize = 8, pages = Math.max(1, Math.ceil(matches.length / pageSize));
  const requestedPage = Number(q.get('page'));
  const page = Math.min(pages, Math.max(1, Number.isInteger(requestedPage) ? requestedPage : 1));
  const { selected, remaining } = selectGames(filtered, archive);
  const change = (values: Record<string, string | null>, replaceQuery = false) => onChange(new URLSearchParams(journeyHref(q, { ...calendarChange, ...values, ...(replaceQuery ? { q: draft.trim() || null, page: null } : {}) }).slice(2)));
  const status = (g: Game) => archiveError ? 'Arquivo de leituras indisponível' : !archive ? 'Conferindo leituras' : availabilityDescription(g, archive);
  const action = (g: Game) => {
    const teams = availabilityTeams(g, archive);
    return archive ? `${availabilityAction(gameAvailability(g, archive))}${teams.length === 1 ? ` · ${teams[0]}` : ''}` : 'Abrir confronto';
  };
  const href = (g: Game) => journeyHref(q, { game: g.gameId });
  function clear() { setDraft(''); change({ q: null, page: null }); searchInput.current?.focus(); }
  const row = (g: Game) => <li key={g.gameId} data-game={g.gameId}>
    <div className="discovery-row-teams"><Participant team={g.awayTeam}/><span className="discovery-versus">×</span><Participant team={g.homeTeam}/></div>
    <div className="discovery-row-context"><p>Semana {g.week} · {dateLabel(g.gameday)}</p><p>{gameState(g).score ?? gameState(g).label}</p><p>{status(g)}</p></div>
    <Link className="journey-action" aria-label={`Abrir confronto ${g.awayTeam.teamAbbr} ${g.homeTeam.teamAbbr}`} to={href(g)}>Abrir confronto</Link>
  </li>;
  return <div className="discovery">
    <section className="discovery-tools" aria-label="Busca e seleção do calendário">
      <form role="search" onSubmit={e => { e.preventDefault(); change({}, true); }}>
        <label htmlFor="game-search">Busque um time ou confronto</label>
        <div className="discovery-search-line"><input ref={searchInput} id="game-search" type="search" autoComplete="off" value={draft} onChange={e => setDraft(e.target.value)} placeholder="Time, cidade ou sigla" aria-describedby="search-hint"/><button className="journey-action" type="submit">Buscar</button>{(draft || query) && <button className="discovery-clear" type="button" onClick={clear}>Limpar</button>}</div>
        <p id="search-hint">Nomes, cidades ou siglas. Somente jogos do calendário.</p>
      </form>
      <details className="discovery-settings"><summary>Semana {week} · {season}<span>{scope === 'season' ? 'Busca na temporada' : 'Busca nesta semana'}{participantsOnly ? ' · com recortes' : ' · todos os jogos'}</span><b>Ajustar seleção e busca</b></summary><div className="discovery-calendar-controls">
        <label>Semana · {season}<select aria-label="Semana" value={week ?? ''} onChange={e => change({ week: e.target.value, page: null, explore: null })}>{[...new Set(games.map(g => g.week))].map(w => <option key={w} value={w}>{w}</option>)}</select></label>
        <label>Buscar em<select aria-label="Buscar em" value={scope} onChange={e => change({ scope: e.target.value }, true)}><option value="week">Esta semana</option><option value="season">Temporada {season}</option></select></label>
        <details className="discovery-filter"><summary>Filtro: {participantsOnly ? 'com recortes' : 'todos os jogos'}</summary><label>Exibir jogos<select aria-label="Exibir jogos" value={q.get('filter') ?? 'all'} onChange={e => change({ filter: e.target.value, page: null, explore: null })}><option value="all">Todos os jogos</option><option value="participants">Com recortes dos participantes</option></select></label></details>
      </div></details>
      {participantsOnly && <p className="discovery-filter-note">“Com recortes” também inclui outros períodos e lacunas; não garante leitura deste jogo.</p>}
    </section>
    {participantsOnly && !archive ? <p role="status">O filtro aguarda a conferência do arquivo. Selecione “Todos os jogos” para explorar o calendário.</p> : searching ? <section className="discovery-results" aria-label="Resultados da busca">
      <div className="discovery-heading"><h2 ref={resultsHeading} tabIndex={-1}>Resultados para “{query}”</h2><p role="status">{matches.length} {matches.length === 1 ? 'jogo' : 'jogos'} · {scope === 'season' ? `temporada ${season}` : `semana ${week}`}{participantsOnly ? ' · com recortes' : ''}</p></div>
      {matches.length ? <><ul className="discovery-rows">{matches.slice((page - 1) * pageSize, page * pageSize).map(row)}</ul>{pages > 1 && <nav className="discovery-pagination" aria-label="Páginas de resultados"><button disabled={page === 1} onClick={() => { change({ page: String(page - 1) }); resultsHeading.current?.focus(); }}>Página anterior</button><span>Página {page} de {pages}</span><button disabled={page === pages} onClick={() => { change({ page: String(page + 1) }); resultsHeading.current?.focus(); }}>Próxima página</button></nav>}</> : <div className="discovery-empty"><h3>Nenhum confronto encontrado.</h3><p>Tente o nome, a cidade ou a sigla de um time. A busca combina os dois participantes quando você informa um confronto.</p><div>{scope === 'week' && <button onClick={() => change({ scope: 'season', page: null })}>Buscar na temporada {season}</button>}{participantsOnly && <button onClick={() => change({ filter: 'all', page: null })}>Incluir jogos sem recortes</button>}<button onClick={clear}>Limpar busca e voltar à semana</button></div></div>}
    </section> : <>
      <div className="discovery-heading"><h2>Em campo na semana {week}</h2><p>Seleção pela disponibilidade de leituras no arquivo.</p></div>
      {!!selected.length && <section className={`discovery-stage${selected.length === 1 ? ' discovery-stage-single' : ''}`} aria-label="Confrontos selecionados">
        <article className="discovery-main" data-game={selected[0].gameId}>
          <div className="discovery-main-meta"><span>{status(selected[0])}</span><span>{dateLabel(selected[0].gameday)}</span></div>
          <h3 className="journey-visually-hidden">{title(selected[0])}</h3>
          <div className="discovery-duel"><Participant large team={selected[0].awayTeam}/><Participant large team={selected[0].homeTeam}/></div>
          <div className="discovery-main-action"><div><strong>{gameState(selected[0]).score ?? `${selected[0].awayTeam.teamAbbr} × ${selected[0].homeTeam.teamAbbr}`}</strong><p>{gameState(selected[0]).label}</p></div><Link className="journey-action" to={href(selected[0])}>{action(selected[0])}</Link></div>
        </article>
        {selected.length > 1 && <div className="discovery-support" aria-label="Mais acessos no arquivo">{selected.slice(1).map(g => <article key={g.gameId} data-game={g.gameId}>
          <p className="discovery-status">{status(g)}</p><h3 className="journey-visually-hidden">{title(g)}</h3><div className="discovery-support-teams"><Participant team={g.awayTeam}/><Participant team={g.homeTeam}/></div><p>{dateLabel(g.gameday)} · {gameState(g).score ?? gameState(g).label}</p><Link className="journey-secondary-action" to={href(g)}>{action(g)}</Link>
        </article>)}</div>}
      </section>}
      {!filtered.length && <div className="discovery-empty"><h3>Nenhum jogo nesta seleção.</h3><p>Altere a semana ou o filtro de jogos.</p><button onClick={() => change({ filter: 'all' })}>Mostrar todos os jogos</button></div>}
      {!!filtered.length && <details className="discovery-archive" open={q.get('explore') === 'open'} onToggle={e => { const open = e.currentTarget.open; if (open !== (q.get('explore') === 'open')) change({ explore: open ? 'open' : null }); }}>
        <summary>Todos os jogos da semana <span>{filtered.length} na seleção · {remaining.length} para explorar</span></summary>
        <p>{selected.length} {selected.length === 1 ? 'confronto já apresentado acima' : 'confrontos já apresentados acima'}; {remaining.length} restantes abaixo. {filtered.length} de {weekGames.length} jogos da semana com o filtro atual.</p>
        {remaining.length ? <ul className="discovery-rows">{remaining.map(row)}</ul> : <p>Todos os confrontos desta seleção já estão apresentados acima.</p>}
      </details>}
    </>}
  </div>;
}
