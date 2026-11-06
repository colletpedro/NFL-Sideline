import {useCallback,useRef} from 'react';
import {useSearchParams} from 'react-router-dom';
import Lab from '../risk-lab/Lab';
import {request} from '../risk-lab/model';
import OutcomesLab from './Lab';
import ProgressionLab from '../progression/Lab';
import {requestProgression} from '../progression/model';
import {requestOutcome} from './model';
import './outcomes.css';
export type IndexLoader=(refresh:boolean,signal:AbortSignal)=>Promise<unknown>;
export default function QuestionEntry(){
 const [q]=useSearchParams(),cache=useRef<{passes?:unknown;interceptions?:unknown;progression?:unknown}>({});
 const loadRisk=useCallback<IndexLoader>(async(refresh,signal)=>{if(!refresh&&cache.current.passes)return cache.current.passes;const value=await request('index.json',signal);if(!signal.aborted)cache.current.passes=value;return value;},[]);
 const loadOutcomes=useCallback<IndexLoader>(async(refresh,signal)=>{if(!refresh&&cache.current.interceptions)return cache.current.interceptions;const value=await requestOutcome('index.json',signal);if(!signal.aborted)cache.current.interceptions=value;return value;},[]);
 const loadProgression=useCallback<IndexLoader>(async(refresh,signal)=>{if(!refresh&&cache.current.progression)return cache.current.progression;const value=await requestProgression('index.json',signal);if(!signal.aborted)cache.current.progression=value;return value;},[]);
 return q.get('reading')==='progression'?<ProgressionLab loadIndex={loadProgression}/>:q.get('reading')==='interceptions'?<OutcomesLab loadIndex={loadOutcomes}/>:<Lab loadIndex={loadRisk}/>;
}
