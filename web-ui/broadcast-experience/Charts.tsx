import { format, mean, playLabels, rate, scoreboard, signed, summarize, teams, type Game, type Period, type PlayType } from './fixtures';
import { epaScale } from './chartScale';

export function EfficiencyChart({ game, period, play }: { game: Game; period: Period; play: PlayType }) {
  const kinds: ('pass' | 'rush')[] = play === 'all' ? ['pass', 'rush'] : [play];
  const scale = epaScale(kinds.flatMap(kind => game.sides.map(s => mean(summarize(s, period, kind)))));
  return <figure className="efficiency-chart"><figcaption><span className="section-kicker">Eficiência</span><h3>Valor por jogada</h3><p>EPA médio · pontos esperados adicionados por jogada</p></figcaption>
    <div className="epa-plot"><div className="epa-axis">{scale.ticks.map((t, i) => <span key={t} style={{ left: `${scale.position(t)}%`, transform: i === 0 ? 'none' : i === scale.ticks.length - 1 ? 'translateX(-100%)' : 'translateX(-50%)' }}>{t === 0 ? '0' : `${t < 0 ? '−' : '+'}${format(Math.abs(t), 2)}`}</span>)}</div>
      {kinds.map(kind => <div className="epa-group" key={kind}><h4>{playLabels[kind]}</h4>{game.sides.map(s => {
        const stat = summarize(s, period, kind), value = mean(stat), team = teams[s.team];
        return <div className={`epa-row ${value === null ? 'metric-absent' : ''}`} key={team.id}><b>{team.id}</b><div className="epa-track" aria-hidden="true">{scale.ticks.map(t => <i className={t === 0 ? 'zero-line' : 'grid-line'} key={t} style={{ left: `${scale.position(t)}%` }}/>) }{value !== null && <span style={{ background: team.color, left: `${scale.position(Math.min(value, 0))}%`, width: `${Math.abs(value) / (scale.max - scale.min) * 100}%` }}/>}</div><strong>{value === null ? stat ? 'Sem jogadas' : 'Sem fonte' : signed(value)}</strong></div>;
      })}</div>)}
    </div><p className="chart-note">EPA positivo indica ganho de pontos esperados; negativo indica perda. Zero é a referência.</p>
  </figure>;
}
export function SuccessChart({ game, period, play }: { game: Game; period: Period; play: PlayType }) {
  return <figure className="success-chart"><figcaption><span className="section-kicker">Frequência</span><h3>Parcela de jogadas com sucesso</h3><p>{playLabels[play]} · sucesso = EPA maior que zero</p></figcaption><div className="success-rows">{game.sides.map(s => {
    const stat = summarize(s, period, play), team = teams[s.team];
    return <div className="success-row" key={team.id}><div className="success-label"><b>{team.id}</b><strong className={stat?.plays ? '' : 'missing-rate'}>{rate(stat)}</strong></div>{stat?.plays ? <><div className="success-track" aria-hidden="true"><span style={{ background: team.color, width: `${stat.success / stat.plays * 100}%` }}/></div><p><b>{stat.success} de {stat.plays}</b> com sucesso<span>{stat.plays - stat.success} sem sucesso</span></p></> : <p className="missing-series">{stat ? 'Nenhuma jogada neste recorte; taxa não calculada.' : 'O recorte não tem cobertura completa. Não é uma taxa de 0%.'}</p>}</div>;
  })}</div><div className="success-axis" aria-hidden="true"><span>0%</span><span>50%</span><span>100%</span></div><p className="chart-note">A parte cinza reúne jogadas com EPA zero ou negativo. Mais sucesso não implica, por si só, uma média maior de EPA.</p></figure>;
}
export function ScoreTimeline({ game }: { game: Game }) {
  const scores = scoreboard(game);
  if (!scores) return null;
  return <table className="quarter-table"><caption>Placar da partida · todos os quartos</caption><thead><tr><th scope="col">Time</th>{[1, 2, 3, 4].map(q => <th scope="col" key={q}>{q}º</th>)}<th scope="col">Final</th></tr></thead><tbody>{game.sides.map((s, i) => <tr key={s.team}><th scope="row">{s.team}</th>{s.quarters!.map((v, q) => <td key={q}>{format(v)}</td>)}<td><b>{scores[i]}</b></td></tr>)}</tbody></table>;
}
