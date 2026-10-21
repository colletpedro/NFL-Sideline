import dal from '../local-editorial/broadcast/assets/dal.png';
import ne from '../local-editorial/broadcast/assets/ne.png';
import bal from '../local-editorial/broadcast/assets/bal.png';

export type TeamId = 'DAL' | 'NE' | 'BAL';
export type Team = { id: TeamId; city: string; name: string; logo: string; color: string; dark: string; optical: number };
export const teams: Record<TeamId, Team> = {
  DAL: { id: 'DAL', city: 'Dallas', name: 'Cowboys', logo: dal, color: '#2463A0', dark: '#0B3057', optical: .76 },
  NE: { id: 'NE', city: 'New England', name: 'Patriots', logo: ne, color: '#C90827', dark: '#870016', optical: 1.1 },
  BAL: { id: 'BAL', city: 'Baltimore', name: 'Ravens', logo: bal, color: '#593D8A', dark: '#25153D', optical: 1.02 },
};
export type PlayType = 'all' | 'pass' | 'rush';
export type Period = 'game' | 'first' | 'second';
export type Sample = { plays: number; success: number; epa: number; yards: number };
export type Half = { pass: Sample; rush: Sample; third: [number, number]; redzone: [number, number] | null };
export type Side = { team: TeamId; quarters: [number, number, number, number]; halves: [Half, Half] };
export type Game = { id: string; round: number; venue: string; title: string; deck: string; angle: string; sides: [Side, Side] };
const sample = (plays: number, success: number, epa: number, yards: number): Sample => ({ plays, success, epa, yards });

// Entirely synthetic scenarios. No season IDs, public DTOs, snapshots or real-game links.
// EPA is a synthetic sum; averages, rates and totals are always derived from these counts.
export const games: Game[] = [
  { id: 'dallas-new-england', round: 7, venue: 'Arlington · Texas', title: 'O passe abre o caminho.',
    deck: 'Dallas constrói a vantagem pelo alto. New England reage depois do intervalo, mas fica a três pontos de mudar o desfecho.',
    angle: 'Dois tempos, duas respostas',
    sides: [
      { team: 'DAL', quarters: [7, 10, 3, 7], halves: [
        { pass: sample(20, 12, 6, 184), rush: sample(14, 6, -.84, 55), third: [4, 7], redzone: [2, 3] },
        { pass: sample(18, 9, 2.16, 128), rush: sample(12, 5, -1.2, 46), third: [3, 6], redzone: [1, 2] },
      ] },
      { team: 'NE', quarters: [3, 7, 7, 7], halves: [
        { pass: sample(17, 7, -2.72, 104), rush: sample(13, 5, .52, 52), third: [2, 7], redzone: [1, 2] },
        { pass: sample(20, 11, 4.6, 162), rush: sample(14, 7, .84, 61), third: [4, 7], redzone: [2, 2] },
      ] },
    ],
  },
  { id: 'baltimore-dallas', round: 6, venue: 'Baltimore · Maryland', title: 'O chão dita o ritmo.',
    deck: 'Baltimore mantém as corridas produtivas nos dois tempos. Dallas encontra espaço no passe, mas o ataque perde eficiência após o intervalo.',
    angle: 'A força do jogo terrestre',
    sides: [
      { team: 'BAL', quarters: [7, 7, 7, 10], halves: [
        { pass: sample(15, 8, 1.2, 112), rush: sample(18, 10, 3.6, 102), third: [3, 6], redzone: null },
        { pass: sample(14, 7, .56, 93), rush: sample(19, 12, 4.56, 118), third: [4, 7], redzone: null },
      ] },
      { team: 'DAL', quarters: [3, 7, 7, 3], halves: [
        { pass: sample(19, 10, 2.28, 143), rush: sample(12, 5, -.36, 42), third: [3, 7], redzone: [1, 2] },
        { pass: sample(20, 8, -2.4, 126), rush: sample(10, 4, -.8, 35), third: [2, 6], redzone: [1, 2] },
      ] },
    ],
  },
  { id: 'new-england-baltimore', round: 8, venue: 'Foxborough · Massachusetts', title: 'Uma posse faz a diferença.',
    deck: 'New England sustenta o passe na segunda metade. Baltimore avança pelo chão, mas não acompanha a produção aérea do adversário.',
    angle: 'Equilíbrio até a última posse',
    sides: [
      { team: 'NE', quarters: [7, 3, 7, 7], halves: [
        { pass: sample(17, 9, 1.7, 130), rush: sample(13, 5, -.65, 44), third: [3, 6], redzone: [1, 2] },
        { pass: sample(18, 11, 3.96, 157), rush: sample(12, 5, -.24, 46), third: [4, 7], redzone: [2, 2] },
      ] },
      { team: 'BAL', quarters: [3, 7, 7, 3], halves: [
        { pass: sample(16, 7, -.8, 99), rush: sample(17, 9, 2.04, 90), third: [2, 6], redzone: [1, 2] },
        { pass: sample(18, 8, -.36, 111), rush: sample(14, 7, 1.12, 68), third: [3, 7], redzone: [1, 2] },
      ] },
    ],
  },
];
export const periodLabels: Record<Period, string> = { game: 'Jogo completo', first: '1º tempo', second: '2º tempo' };
export const playLabels: Record<PlayType, string> = { all: 'Todas as jogadas', pass: 'Passe', rush: 'Corrida' };
export const score = (side: Side) => side.quarters.reduce((a, b) => a + b, 0);
export function halves(side: Side, period: Period): Half[] {
  return period === 'game' ? side.halves : [side.halves[period === 'first' ? 0 : 1]];
}
export function summarize(side: Side, period: Period, play: PlayType): Sample {
  return halves(side, period).flatMap(half => play === 'all' ? [half.pass, half.rush] : [half[play]])
    .reduce((a, b) => ({ plays: a.plays + b.plays, success: a.success + b.success, epa: a.epa + b.epa, yards: a.yards + b.yards }), { plays: 0, success: 0, epa: 0, yards: 0 });
}
export function countPair(side: Side, period: Period, key: 'third' | 'redzone'): [number, number] | null {
  const values = halves(side, period).map(h => h[key]);
  if (values.some(x => x === null)) return null;
  return values.reduce<[number, number]>((a, b) => [a[0] + b![0], a[1] + b![1]], [0, 0]);
}
export const format = (n: number, digits = 0) => n.toLocaleString('pt-BR', { minimumFractionDigits: digits, maximumFractionDigits: digits });
export const signed = (n: number) => `${n < 0 ? '−' : '+'}${format(Math.abs(n), 3)}`;
export const rate = (s: Sample) => s.plays ? `${format(s.success / s.plays * 100, 1)}%` : 'Sem amostra';
export const pair = (p: [number, number] | null) => p ? `${p[0]}/${p[1]}` : 'Não disponível';
