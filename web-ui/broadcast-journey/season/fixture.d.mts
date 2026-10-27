import type {SeasonIndex,Matchup,SeasonTeam} from './model';
export function fixture():{index:SeasonIndex;games:Record<string,Matchup>;teams:Record<string,SeasonTeam>}|null;
