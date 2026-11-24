import type {TeamIndex,TeamDocument} from './model';
import type {Index} from '../w12/model';
export function teamFixture():null|{index:TeamIndex;docs:Record<string,TeamDocument>;matchupIndex:Index;oracle:{rounding:Record<string,string>}};
