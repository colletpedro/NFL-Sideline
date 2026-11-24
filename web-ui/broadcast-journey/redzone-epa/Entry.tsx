import {useSearchParams} from 'react-router-dom';
import {Entry as RankedEntry} from '../ranking-redzone/Entry';
import {RedzoneEpaProvider} from './Provider';
export function Entry(){const [q]=useSearchParams();return [null,'matchup-w12','team-w12'].includes(q.get('view'))?<RedzoneEpaProvider><RankedEntry/></RedzoneEpaProvider>:<RankedEntry/>;}
