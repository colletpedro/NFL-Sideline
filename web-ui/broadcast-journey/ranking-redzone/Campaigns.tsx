import type {Campaign} from '../w12/model';
const outcomes:Record<string,{short:string;label:string;shape:React.ReactNode}>={
 TOUCHDOWN:{short:'TD',label:'Touchdown ofensivo',shape:<><path d="M5 27C3 15 15 3 27 5c2 12-10 24-22 22Z"/><path d="m10 22 12-12m-8 4 4 4m-7-1 4 4m2-10 4 4M5 22l5 5M22 5l5 5"/></>},
 FIELD_GOAL:{short:'FG',label:'Field goal convertido',shape:<><path d="M7 4v15h18V4M16 19v10"/><ellipse cx="16" cy="8" rx="2" ry="4" transform="rotate(30 16 8)"/></>},
 MISSED_FIELD_GOAL:{short:'FG perdido',label:'Field goal perdido ou bloqueado',shape:<><path d="M6 4v15h17V4M15 19v10M25 24l5 5m0-5-5 5M10 6l6 6m0-6-6 6"/></>},
 TURNOVER:{short:'Turnover',label:'Turnover — mudança de posse',shape:<><path d="M26 25V13a6 6 0 0 0-6-6H5m7-5L5 7l7 6"/><path d="M5 22h10m-4-4 4 4-4 4"/></>},
 OPPONENT_TOUCHDOWN:{short:'TD adversário',label:'Touchdown do time que defendia',shape:<><path d="M7 23C5 15 13 7 23 9c1 8-7 16-16 14Zm4-4 8-6m-6 2 3 3M26 4H5l5-3M5 4l5 4"/></>},
 DOWNS:{short:'Descidas',label:'Perda por descidas',shape:<><path d="M16 3v17m-6-6 6 6 6-6M6 27h20"/><path d="M5 5h3M5 10h3M5 15h3M5 20h3"/></>},
 PUNT:{short:'Punt',label:'Punt',shape:<><path d="m5 27 8-4-3-6-4 2-3-1v9h9M15 15 27 3m-7 0h7v7"/><ellipse cx="23" cy="19" rx="3" ry="5" transform="rotate(35 23 19)"/></>},
 END_HALF_GAME:{short:'Fim de tempo',label:'Fim de tempo ou jogo',shape:<><circle cx="16" cy="17" r="11"/><path d="M16 10v8l5 3M12 2h8"/></>},
 SAFETY:{short:'Safety',label:'Safety',shape:<><path d="m16 3 11 4v9c0 6-5 10-11 13C10 26 5 22 5 16V7Z"/><path d="M12 13c0-5 8-5 8 0 0 3-8 6-8 9h8"/></>},
};
const campaignOutcome=(outcome:string)=>outcomes[outcome]??{short:outcome,label:outcome,shape:<><circle cx="16" cy="16" r="12"/><path d="M16 8v10m0 5v1"/></>};
export function CampaignGlyph({outcome}:{outcome:string}) {return <>{campaignOutcome(outcome).shape}</>;}
export function CampaignSymbol({outcome}:{outcome:string}) {return <svg className="rr-campaign-symbol" viewBox="0 0 32 32" aria-hidden="true" data-outcome-symbol={outcome}>{campaignOutcome(outcome).shape}</svg>;}
export function CampaignLegend({outcomes:values}:{outcomes:string[]}) {
 const relevant=[...new Set(values)];
 if(!relevant.length)return null;
 return <ul className="rr-campaign-legend" aria-label="Legenda dos desfechos das campanhas">{relevant.map(outcome=><li key={outcome}><CampaignSymbol outcome={outcome}/><span>{campaignOutcome(outcome).label}</span></li>)}</ul>;
}
export function CampaignMark({unit:u,label,scope,selected,onSelect}:{unit:Campaign;label:string;scope:'game'|'team';selected:boolean;onSelect:()=>void}) {
 const outcome=campaignOutcome(u.outcome);
 return <button type="button" className="rr-campaign-mark" {...(scope==='game'?{'data-campaign-mark':u.id}:{'data-team-campaign':u.id})} data-campaign-outcome={u.outcome} aria-pressed={selected} onClick={onSelect} aria-label={`${label}, ${u.offense} contra ${u.defense}, W${u.week}, campanha ${u.fixedDrive}, ${outcome.label}`}><CampaignSymbol outcome={u.outcome}/><span><strong>{outcome.short}</strong> · {scope==='team'?`W${u.week} · `:''}<span className="rr-campaign-id">Campanha {u.fixedDrive}</span></span></button>;
}
