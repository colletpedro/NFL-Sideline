import dalLogo from '../broadcast/assets/dal.png';
import neLogo from '../broadcast/assets/ne.png';

export type SimulationTeam = {
  code: 'DAL' | 'NE'; city: string; nickname: string; logo: string; score: number;
};
export type Simulation = {
  kind: 'VISUAL_SIMULATION'; disclosure: string; heading: string; context: string;
  teams: readonly [SimulationTeam, SimulationTeam];
  passing: { yards: number; touchdowns: number };
  secondHalf: { points: number };
  thirdDown: { converted: number; attempts: number };
};

// Visual-only scenario. No season, game ID, DTO, API or snapshot association.
export const matchupSimulation = {
  kind: 'VISUAL_SIMULATION',
  disclosure: 'Simulação visual — confronto e números fictícios',
  heading: 'Resumo do jogo',
  context: 'Confronto simulado',
  teams: [
    { code: 'DAL', city: 'Dallas', nickname: 'Cowboys', logo: dalLogo, score: 27 },
    { code: 'NE', city: 'New England', nickname: 'Patriots', logo: neLogo, score: 24 },
  ],
  passing: { yards: 312, touchdowns: 2 },
  secondHalf: { points: 14 },
  thirdDown: { converted: 7, attempts: 13 },
} as const satisfies Simulation;

// Editorial copy derives from the scenario; there is one source for every number.
export function recapCopy(s: Simulation) {
  const [dallas, patriots] = s.teams;
  return {
    headline: [`${dallas.city} vence os ${patriots.nickname}`, `por ${dallas.score} a ${patriots.score} no confronto`],
    facts: [
      { key: 'passing', lines: [`${dallas.nickname}: ${s.passing.yards} jardas aéreas`, `e ${s.passing.touchdowns} touchdowns em passes`] },
      { key: 'second-half', lines: [`${patriots.nickname} marcam ${s.secondHalf.points} pontos`, 'na segunda metade do jogo'] },
      { key: 'third-down', lines: [`${dallas.city} converte ${s.thirdDown.converted} de ${s.thirdDown.attempts}`, 'tentativas de terceira descida'] },
    ],
  };
}
