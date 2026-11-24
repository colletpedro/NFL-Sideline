// Proveniência dos números de avaliação do B2: lida de provenance.json (gerado do MLflow por
// research/mlflow_tracking/cli.py provenance). Nenhum número de métrica fica digitado no código.
import raw from './provenance.json';
import {B2_SHA} from './model';
export type Sourced={value:number;runId:string;metricKey?:string;paramKey?:string};
export type ModelProvenance={name:string;version:string;runId:string;experiment:string;numbers:Record<string,Sourced>};
export type Provenance={schemaVersion:1;models:Record<string,ModelProvenance>};
export const B2_KEYS=['all.observed_interceptions','all.expected_interceptions','all.log_loss','all.brier','all.average_precision','all.roc_auc','ftn_0.observed_interceptions','ftn_0.expected_interceptions','ftn_1.observed_interceptions','ftn_1.expected_interceptions'].map(k=>`evaluation2025.B2.${k}`).concat(['evaluation2025.B1.all.log_loss','evaluation2025.C.all.log_loss','evaluation2025.bootstrap.replicates']);
const isObj=(v:unknown):v is Record<string,unknown>=>typeof v==='object'&&v!==null&&!Array.isArray(v);
const text=(v:unknown)=>typeof v==='string'&&v.length>0;
/** Valida estritamente; devolve o modelo `sha` ou null se algo faltar, divergir ou não for finito. */
export function evaluationFor(value:unknown,sha:string):ModelProvenance|null{
 if(!isObj(value)||value.schemaVersion!==1||!isObj(value.models))return null;
 const m=value.models[sha];
 if(!isObj(m)||!text(m.name)||!text(m.version)||!text(m.runId)||!text(m.experiment)||!isObj(m.numbers))return null;
 const numbers=m.numbers as Record<string,unknown>;
 for(const key of B2_KEYS){const n=numbers[key];if(!isObj(n)||typeof n.value!=='number'||!Number.isFinite(n.value)||!text(n.runId)||!(text(n.metricKey)||text(n.paramKey)))return null;}
 const reps=(numbers['evaluation2025.bootstrap.replicates'] as Sourced).value;
 if(!Number.isInteger(reps)||reps<=0)return null;
 return m as unknown as ModelProvenance;
}
export const bundledProvenance:unknown=raw;
export const activeEvaluation=(sha:string,source:unknown=raw)=>sha===B2_SHA?evaluationFor(source,sha):null;
const fixed=(x:number,d:number)=>x.toFixed(d).replace('.',',');
const grouped=(x:number)=>String(Math.round(x)).replace(/\B(?=(\d{3})+(?!\d))/g,'.');
/** Formatação pt-BR determinística (sem depender de ICU). */
export const fmt={int:grouped,two:(x:number)=>fixed(x,2),six:(x:number)=>fixed(x,6)};
