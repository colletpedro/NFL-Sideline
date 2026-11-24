import type {CSSProperties} from 'react';
import {teamIdentity} from '../../broadcast-real/identity';
export const teamStyle=(team:string)=>{const v=teamIdentity(team);return {'--team':v.color,'--team-dark':v.dark,'--logo-contrast-filter':v.logoPlate?'brightness(0) invert(1)':'none'} as CSSProperties;};
