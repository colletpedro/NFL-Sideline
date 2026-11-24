import type {OutcomeCounts} from './model';
import {interceptionNumber,interceptionSigned} from './communication';
import {outcomeLabels} from './communication';
export function OutcomeMetrics({c}:{c:OutcomeCounts}){return <dl className="rl-three ro-three" aria-label="Interceptações sofridas, esperadas e diferença no mesmo conjunto de passes">
 <div data-metric="observed-interceptions"><dt>{outcomeLabels.observed}</dt><dd>{c.eligiblePasses?c.observedInterceptions:'—'}</dd><small>Desfecho registrado no PBP</small></div>
 <div data-metric="expected-interceptions"><dt>{outcomeLabels.expected}</dt><dd>{c.eligiblePasses?interceptionNumber(c.expectedInterceptions):'—'}</dd><small>Soma das probabilidades da referência B2</small></div>
 <div data-metric="difference-interceptions"><dt>{outcomeLabels.difference}</dt><dd>{c.eligiblePasses?interceptionSigned(c.differenceInterceptions):'—'}</dd><small>Diferença descritiva, sem atribuição de causa</small></div>
 </dl>;}
export function OutcomeExplanation({name,c}:{name:string;c:OutcomeCounts}){return c.eligiblePasses?<p className="ro-explanation">{name} sofreu <strong>{c.observedInterceptions}</strong> {c.observedInterceptions===1?'interceptação':'interceptações'}; a referência estimava aproximadamente <strong>{interceptionNumber(c.expectedInterceptions)}</strong> para esses passes. São <strong>{interceptionNumber(Math.abs(c.differenceInterceptions))}</strong> {c.differenceInterceptions>=0?'a mais':'a menos'} que a estimativa.</p>:<p role="status">Sem passes elegíveis deste jogador no período selecionado. Nenhum valor de outro período foi usado.</p>;}
