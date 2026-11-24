import { Link } from 'react-router-dom';
import type { Game } from '../src/services/types';
import { Reading } from '../broadcast-real/Reading';
import { period as periodLabel } from '../local-editorial/observations/selection';
import { foundations, sides, choiceGroups } from './choice';
import { liveSelection, readingPeriod } from './liveSelection';
import { relation, relationText } from './relations';
import { journeyHref } from './state';
import type { Archive } from './sources';

type Props = { game: Game; archive: Archive; q: URLSearchParams; memberLabels: Record<string,string>; onChoice: (change: Record<string,string>) => void; onQuery: (q: URLSearchParams) => void };
export function LiveReading({ game, archive, q, memberLabels, onChoice, onQuery }: Props) {
  const selection = liveSelection(game, archive, q), { choice, target } = selection;
  const groups = choiceGroups(game, archive, choice);
  const other = [...groups.other, ...groups.archive];
  const changeDetail = (key: string, open: boolean) => onQuery(new URLSearchParams(journeyHref(q, { [key]: open ? 'open' : null }).slice(2)));
  return <section className="live-reading" aria-label="Leitura dinâmica do confronto">
    <div className="live-controls">
      <div className="live-control-heading"><h2>O jogo, no seu recorte.</h2><p>Troque a seleção e veja os números abaixo.</p></div>
      <div className="live-dimensions">
        <fieldset><legend>Lado da bola</legend><div>{Object.entries(sides).map(([side,label]) => <button type="button" key={side} aria-pressed={choice.side === side} onClick={() => onChoice({side})}>{label}</button>)}</div></fieldset>
        <fieldset><legend>Fundamento</legend><div>{Object.entries(foundations).map(([play,label]) => <button type="button" key={play} aria-pressed={choice.play === play} onClick={() => onChoice({play})}>{label}</button>)}</div></fieldset>
      </div>
      <fieldset className="live-periods"><legend>Período da leitura</legend><div><button type="button" aria-pressed={selection.period === 'game'} onClick={() => onChoice({reading:'game'})}>Deste jogo</button>
        {groups.includes.map(({d,entry}) => <button type="button" key={entry.entryId+d.observationId} aria-label={`Semanas ${d.request.period.weeks.join('–')} · inclui este jogo`} aria-pressed={selection.period === readingPeriod(d)} onClick={() => onChoice({reading:readingPeriod(d)})}>Semanas {d.request.period.weeks.join('–')}</button>)}
      </div></fieldset>
      <p className="live-announcement" role="status" aria-live="polite" aria-atomic="true">{choice.team} · {sides[choice.side]} · {foundations[choice.play]} · {selection.period === 'game' ? 'Deste jogo' : target ? periodLabel(target.d) : 'Período escolhido'}{!target && !selection.error ? ' · Sem leitura disponível' : ''}</p>
    </div>
    {selection.error ? <div className="real-state" role="alert"><h2>Recorte não confirmado.</h2><p>{selection.error}</p><button type="button" className="journey-action" onClick={() => onChoice({reading:'game'})}>Mostrar seleção deste jogo</button></div> : target ? <>
      <p className="live-relation" data-relation={relation(game,target.d)}>{relationText(relation(game,target.d),target.d)}</p>
      <Reading guided key={archive.catalog.sessionId+'|'+target.entry.entryId+'|'+target.d.observationId} d={target.d} entry={target.entry} memberLabels={memberLabels} detailsOpen={q.get('details') === 'open'} compositionOpen={q.get('composition') === 'open'} onDetailsChange={open => changeDetail('details',open)} onCompositionChange={open => changeDetail('composition',open)}/>
    </> : <div className="live-no-reading"><h3>Sem leitura deste recorte.</h3><p>O arquivo não oferece os dados desta seleção. Escolha outro período disponível ou outro participante; nenhum número de outro jogo foi usado.</p></div>}
    {!!other.length && <details className="live-other"><summary>Outros períodos de {choice.team}</summary><ul>{other.map(({d,entry}) => <li key={entry.entryId+d.observationId}><Link to={journeyHref(q,{team:d.subject.team,side:d.subject.role,play:d.subject.foundation,reading:readingPeriod(d),entry:entry.entryId,observation:d.observationId})}>{periodLabel(d)}</Link><span>{relationText(relation(game,d),d)}</span></li>)}</ul></details>}
  </section>;
}
