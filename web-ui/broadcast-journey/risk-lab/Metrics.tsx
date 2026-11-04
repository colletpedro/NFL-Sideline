import type {Counts} from './model';
import {metricLabels,number} from './communication';
export function Metrics({c}:{c:Counts}){return <dl className="rl-three" aria-label="Classificação, estimativa e desfecho no mesmo conjunto de passes">
 <div data-metric="classified"><dt>{metricLabels.classified}</dt><dd>{c.observed}</dd><small>Classificação do provedor FTN</small></div>
 <div data-metric="expected"><dt>{metricLabels.expected}</dt><dd>{number(c.expected,2)}</dd><small>Soma das probabilidades do M3</small></div>
 <div data-metric="interceptions"><dt>{metricLabels.interceptions}</dt><dd>{c.interceptions}</dd><small>O que aconteceu nesses passes</small></div>
 </dl>;}
