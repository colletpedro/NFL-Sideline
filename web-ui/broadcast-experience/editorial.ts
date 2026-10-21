import { mean, periodLabels, playLabels, successRate, summarize, teams, type Game, type Period, type PlayType, type TeamId } from './fixtures';

// Presentation rules for synthetic demonstrations only. These are descriptive thresholds,
// not confidence intervals, significance tests or an editorial policy for real observations.
export const MIN_PLAYS = 10;
export const EPA_CLOSE = .01;
export const SUCCESS_CLOSE = .02;
export type ReadingDecision = 'pregame' | 'unavailable' | 'insufficient' | 'cross' | 'split' | 'divergence' | 'precision' | 'close' | 'efficiency';
export type Reading = {
  decision: ReadingDecision; title: string; text: string;
  context: { period: Period; play: PlayType; label: string };
  samples: { team: TeamId; plays: number | null; epa: number | null; success: number | null; yards: number | null }[];
  evidence: { metric: 'epaGap' | 'successGap' | 'passGap' | 'rushGap'; label: string; value: number; unit: 'EPA/jogada' | 'p.p.' }[];
};
const rounded = (n: number, digits: number) => Number(n.toFixed(digits));
const direction = (a: number, b: number, threshold: number, digits: number) =>
  rounded(a, digits) === rounded(b, digits) || Math.abs(a - b) <= threshold + 1e-10 ? 0 : a > b ? 1 : -1;

export function readSlice(game: Game, period: Period, play: PlayType): Reading {
  const stats = game.sides.map(s => game.status === 'pregame' ? null : summarize(s, period, play));
  const samples = stats.map((s, i) => ({ team: game.sides[i].team, plays: s?.plays ?? null, epa: mean(s), success: successRate(s), yards: s?.yards ?? null }));
  const context = { period, play, label: `${periodLabels[period]} · ${playLabels[play]}` };
  const result = (decision: ReadingDecision, title: string, text: string, evidence: Reading['evidence'] = []): Reading => ({ decision, title, text, context, samples, evidence });
  if (game.status === 'pregame') return result('pregame', 'A bola ainda não está em jogo.', 'Esta partida ainda não tem jogadas. Não há desempenho do confronto nem histórico sintético oferecido para comparar.');
  const absent = samples.filter(s => s.plays === null).map(s => teams[s.team].city);
  if (absent.length) return result('unavailable', 'Falta uma parte deste recorte.', `${absent.join(' e ')} ${play === 'all' ? 'sem cobertura completa de passe e corrida' : `sem fonte para ${playLabels[play].toLowerCase()}`} neste período. Os valores disponíveis continuam visíveis; não há comparação completa.`);
  if (samples.some(s => s.plays! < MIN_PLAYS)) return result('insufficient', 'Amostra curta para comparar.', `Há menos de ${MIN_PLAYS} jogadas em pelo menos um ataque. Os números descrevem o recorte, mas esta demonstração não escolhe uma leitura comparativa.`);
  const [a, b] = samples, names = samples.map(s => teams[s.team].city);
  const epaOrder = direction(a.epa!, b.epa!, EPA_CLOSE, 3), successOrder = direction(a.success!, b.success!, SUCCESS_CLOSE, 3);
  const lead = epaOrder > 0 ? 0 : 1, other = 1 - lead;
  const epaEvidence: Reading['evidence'] = [{ metric: 'epaGap', label: 'Diferença entre médias', value: Math.abs(a.epa! - b.epa!), unit: 'EPA/jogada' }];
  const successEvidence: Reading['evidence'] = [{ metric: 'successGap', label: 'Diferença de sucesso', value: Math.abs(a.success! - b.success!) * 100, unit: 'p.p.' }];
  const foundation = play === 'pass' ? 'no passe' : play === 'rush' ? 'na corrida' : 'nas jogadas selecionadas';

  if (epaOrder * successOrder < 0) {
    const signs = rounded(a.epa!, 3) * rounded(b.epa!, 3) < 0;
    const efficiency = signs ? `${names[lead]} produziu EPA positivo e ${names[other]}, negativo` : `${names[lead]} teve o maior EPA por jogada`;
    return result('divergence', 'Maior EPA, menos sucesso.', `${efficiency}; ${names[other]} teve sucesso em uma parcela maior das jogadas.`, [...epaEvidence, ...successEvidence]);
  }

  if (play === 'all') {
    const pass = game.sides.map(s => summarize(s, period, 'pass')), rush = game.sides.map(s => summarize(s, period, 'rush'));
    if ([...pass, ...rush].every(s => s && s.plays >= MIN_PLAYS)) {
      const pd = direction(mean(pass[0])!, mean(pass[1])!, EPA_CLOSE, 3), rd = direction(mean(rush[0])!, mean(rush[1])!, EPA_CLOSE, 3);
      if (pd * rd < 0) {
        const p = pd > 0 ? 0 : 1, r = 1 - p;
        return result('cross', `${game.sides[p].team} no passe; ${game.sides[r].team} na corrida.`, `${names[p]} teve maior EPA por passe; ${names[r]}, maior EPA por corrida.`, [
          { metric: 'passGap', label: 'Diferença no passe', value: Math.abs(mean(pass[0])! - mean(pass[1])!), unit: 'EPA/jogada' },
          { metric: 'rushGap', label: 'Diferença na corrida', value: Math.abs(mean(rush[0])! - mean(rush[1])!), unit: 'EPA/jogada' },
        ]);
      }
    }
  }
  if (!epaOrder) {
    const sameDisplay = rounded(a.epa!, 3) === rounded(b.epa!, 3);
    const successText = successOrder ? ` ${names[successOrder > 0 ? 0 : 1]} teve sucesso em uma parcela maior das jogadas.` : ' A frequência de sucesso também ficou próxima.';
    return result(sameDisplay ? 'precision' : 'close', sameDisplay ? 'Mesmo EPA na precisão exibida.' : 'Médias de EPA próximas.',
      (sameDisplay ? 'As médias coincidem com três casas decimais; essa apresentação não distingue uma ordem de EPA.' : 'A diferença não ultrapassa 0,010 EPA por jogada, limite descritivo desta demonstração.') + successText,
      successOrder ? successEvidence : epaEvidence);
  }
  if (rounded(a.epa!, 3) * rounded(b.epa!, 3) < 0) {
    const positive = a.epa! > 0 ? 0 : 1, negative = 1 - positive;
    return result('split', `${game.sides[positive].team} soma valor; ${game.sides[negative].team} perde.`, `${names[positive]} produziu EPA positivo ${foundation}; ${names[negative]} perdeu valor nesse fundamento.`, epaEvidence);
  }
  if (rounded(samples[other].epa!, 3) === 0) return result('efficiency', `${game.sides[lead].team} soma valor; ${game.sides[other].team} fica em zero.`, `${names[lead]} produziu EPA positivo ${foundation}; a média de ${names[other]} ficou em zero na precisão exibida.`, epaEvidence);
  if (rounded(samples[lead].epa!, 3) === 0) return result('efficiency', `${game.sides[lead].team} fica em zero; ${game.sides[other].team} perde.`, `${names[lead]} ficou em zero na precisão exibida; ${names[other]} produziu EPA negativo ${foundation}.`, epaEvidence);
  const bothNegative = a.epa! < 0 && b.epa! < 0;
  const volumeText = samples[other].plays! - samples[lead].plays! >= 5 ? ` ${names[other]} executou mais jogadas, sem ter a maior média de EPA.` : '';
  return result('efficiency', bothNegative ? `${game.sides[lead].team} perde menos valor.` : `${game.sides[lead].team} tem maior EPA por jogada.`,
    (bothNegative ? `Os dois ataques tiveram EPA negativo ${foundation}; a média de ${names[lead]} foi menos negativa.` : `${names[lead]} teve a maior média de EPA ${foundation}, considerando apenas o período selecionado.`) + volumeText, epaEvidence);
}

export function recoverySlices(game: Game, period: Period, play: PlayType) {
  const candidates: [Period, PlayType][] = [[period, 'rush'], [period, 'pass'], ['first', play], ['second', play], ['first', 'all']];
  return candidates.filter(([p, f], i) => !(p === period && f === play) && candidates.findIndex(c => c[0] === p && c[1] === f) === i)
    .filter(([p, f]) => game.sides.every(s => { const value = summarize(s, p, f); return value && value.plays >= MIN_PLAYS; })).slice(0, 2);
}
