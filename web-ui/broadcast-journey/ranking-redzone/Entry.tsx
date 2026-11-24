import {useSearchParams} from 'react-router-dom';
import {Route} from '../hub-team/Route';
import {ReadingPolishContext} from '../reading-polish/context';
import {RankingRedzoneContext} from './context';
export function Entry(){const [q]=useSearchParams();const enabled=[null,'matchup-w12','team-w12'].includes(q.get('view'));return <ReadingPolishContext.Provider value={enabled}><RankingRedzoneContext.Provider value={enabled}><div className={enabled?'rp rr':undefined}><Route/></div></RankingRedzoneContext.Provider></ReadingPolishContext.Provider>;}
