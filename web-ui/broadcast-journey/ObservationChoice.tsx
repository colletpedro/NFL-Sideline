import type { CSSProperties } from 'react';
import { Link } from 'react-router-dom';
import type { Game } from '../src/services/types';
import type { DTO } from '../local-editorial/observations/model';
import { Logo } from '../broadcast-experience/TeamLogo';
import { teamIdentity } from '../broadcast-real/identity';
import { period } from '../local-editorial/observations/selection';
import type { Archive } from './sources';
import { relation, relationText } from './relations';
import { choiceGroups, readChoice, sides, foundations, type Choice } from './choice';

type Props = { teamPicker?: boolean; game: Game; archive: Archive; q: URLSearchParams; selected?: DTO; onChoice: (change: Record<string, string>) => void; href: (entry: string, observation: string) => string };
export function ObservationChoice({ teamPicker = true, game, archive, q, selected, onChoice, href }: Props) {
  const choice = readChoice(game, q, selected), grouped = choiceGroups(game, archive, choice);
  const teams = [game.awayTeam, game.homeTeam];
  const context = `${choice.team} · ${sides[choice.side]} · ${foundations[choice.play]}`;
  function recuts(items: Archive['documents'], group: 'includes' | 'other' | 'archive', label: string) {
    if (!items.length) return null;
    return <details className="journey-recuts"><summary>{label} <span>{items.length === 1 ? '1 recorte' : `${items.length} recortes`}</span></summary>
      <ul>{items.map(({ d, entry }) => <li key={entry.entryId + d.observationId}>
        <div><h3>{period(d)}</h3><p>{relationText(group, d)}</p></div>
        <Link className="journey-secondary-action" to={href(entry.entryId, d.observationId)} aria-label={`Abrir ${context}, ${period(d)}`}>{group === 'archive' ? 'Abrir arquivo separado' : 'Abrir período'}</Link>
      </li>)}</ul>
    </details>;
  }
  return <section className="journey-choice" aria-labelledby="journey-choice-title">
    <div className="journey-choice-heading"><h2 id="journey-choice-title">Escolha sua leitura</h2><p>{teamPicker ? 'Escolha um time e o que quer observar.' : 'Selecione o lado da bola e o fundamento.'}</p></div>
    {teamPicker && <fieldset className="journey-pick-team"><legend>Time</legend><div>{teams.map(t => {
      const identity = teamIdentity(t.teamAbbr);
      return <button type="button" key={t.teamAbbr} aria-pressed={choice.team === t.teamAbbr} onClick={() => onChoice({ team: t.teamAbbr })} style={{ '--team': identity.color, '--team-dark': identity.dark } as CSSProperties}>
        <Logo team={identity}/><span><strong>{t.teamName}</strong><small>{t.teamAbbr}</small></span>
      </button>;
    })}</div></fieldset>}
    <div className="journey-pick-controls">
      <fieldset><legend>Lado da bola</legend><div>{(Object.entries(sides) as [Choice['side'], string][]).map(([key, label]) => <button key={key} aria-pressed={choice.side === key} onClick={() => onChoice({ side: key })}>{label}</button>)}</div></fieldset>
      <fieldset><legend>Fundamento</legend><div>{(Object.entries(foundations) as [Choice['play'], string][]).map(([key, label]) => <button key={key} aria-pressed={choice.play === key} onClick={() => onChoice({ play: key })}>{label}</button>)}</div></fieldset>
    </div>
    <div className="journey-choice-result" aria-live="polite" aria-atomic="true">
      <p className="journey-choice-context">{context}</p>
      {grouped.primary.length ? grouped.primary.map(({ d, entry }) => {
        const isGap = relation(game, d) === 'gap';
        return <div className="journey-choice-offer" key={entry.entryId + d.observationId}><div>
          <h3>{isGap ? 'Sem fonte para este jogo' : 'Leia a amostra deste jogo'}</h3>
          <p>{period(d)}</p>
          <p>{isGap ? relationText('gap', d) : 'Jogadas observadas deste time na partida. Completude não confirmada.'}</p>
        </div><Link className="journey-action" to={href(entry.entryId, d.observationId)}>{isGap ? `Ver lacuna de ${choice.team}` : `Abrir leitura de ${choice.team}`}</Link></div>;
      }) : <div className="journey-choice-offer"><div><h3>Sem leitura exclusiva deste jogo</h3><p>O arquivo não oferece essa combinação para a partida.{grouped.includes.length + grouped.other.length + grouped.archive.length > 0 ? ' Explore os períodos disponíveis abaixo.' : ' Tente o outro time ou volte ao calendário.'}</p></div></div>}
    </div>
    <div className="journey-other-periods">
      {recuts(grouped.includes, 'includes', 'Períodos que incluem este jogo')}
      {recuts(grouped.other, 'other', 'Outros períodos deste time')}
      {recuts(grouped.archive, 'archive', 'Outra temporada ou fase')}
    </div>
    <p className="journey-choice-limit">Uma leitura descreve um time e sua amostra. Não é comparação entre os participantes nem evidência pregame.</p>
  </section>;
}
