import { format, playLabels, rate, signed, summarize, teams, type Game, type Period, type PlayType } from './fixtures';

// Fixed signed axis shared by every scenario and selection: −0.20 … +0.40 EPA/play.
const position = (value: number) => (value + .2) / .6 * 100;
export function EfficiencyChart({ game, period, play }: { game: Game; period: Period; play: PlayType }) {
  const kinds: ('pass' | 'rush')[] = play === 'all' ? ['pass', 'rush'] : [play];
  return <figure className="efficiency-chart"><figcaption><span className="section-kicker">Eficiência</span><h3>O que cada jogada produz</h3><p>EPA médio por jogada · ataque</p></figcaption>
    <div className="epa-plot"><div className="epa-axis"><span>−0,20</span><span>0</span><span>+0,20</span><span>+0,40</span></div>
      {kinds.map(kind => <div className="epa-group" key={kind}><h4>{playLabels[kind]}</h4>{game.sides.map(s => {
        const stat = summarize(s, period, kind), value = stat.plays ? stat.epa / stat.plays : null, team = teams[s.team];
        return <div className="epa-row" key={team.id}><b>{team.id}</b><div className="epa-track" aria-hidden="true"><i className="grid-line grid-one"/><i className="zero-line"/><i className="grid-line grid-two"/>{value !== null && <span style={{ background: team.color, left: `${position(Math.min(value, 0))}%`, width: `${Math.abs(value) / .6 * 100}%` }}/>}</div><strong>{value === null ? 'Sem amostra' : signed(value)}</strong></div>;
      })}</div>)}
    </div><p className="chart-note">Zero é a referência: valores negativos indicam perda de pontos esperados. As cores identificam os times.</p>
  </figure>;
}
export function SuccessChart({ game, period, play }: { game: Game; period: Period; play: PlayType }) {
  return <figure className="success-chart"><figcaption><span className="section-kicker">Consistência</span><h3>Quantas jogadas dão certo?</h3><p>Sucesso · {playLabels[play].toLocaleLowerCase('pt-BR')}</p></figcaption><div className="success-rows">{game.sides.map(s => {
    const stat = summarize(s, period, play), team = teams[s.team];
    return <div className="success-row" key={team.id}><div className="success-label"><b>{team.id}</b><strong>{rate(stat)}</strong></div><div className="success-track" aria-hidden="true"><span style={{ background: team.color, width: `${stat.plays ? stat.success / stat.plays * 100 : 0}%` }}/></div><p><b>{stat.success} de {stat.plays}</b> com sucesso<span>{stat.plays - stat.success} sem sucesso</span></p></div>;
  })}</div><div className="success-axis" aria-hidden="true"><span>0%</span><span>50%</span><span>100%</span></div><p className="chart-note">Sucesso = EPA maior que zero. A parte cinza reúne jogadas com EPA zero ou negativo.</p></figure>;
}
export function ScoreTimeline({ game }: { game: Game }) {
  return <table className="quarter-table"><caption>Placar por quarto</caption><thead><tr><th scope="col">Time</th>{[1, 2, 3, 4].map(q => <th scope="col" key={q}>{q}º</th>)}<th scope="col">Final</th></tr></thead><tbody>{game.sides.map(s => <tr key={s.team}><th scope="row">{s.team}</th>{s.quarters.map((v, i) => <td key={i}>{format(v)}</td>)}<td><b>{s.quarters.reduce((a, b) => a + b, 0)}</b></td></tr>)}</tbody></table>;
}
