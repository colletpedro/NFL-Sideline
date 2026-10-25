import {Link} from 'react-router-dom';
import {Logo} from '../../broadcast-experience/TeamLogo';
import {teamIdentity} from '../../broadcast-real/identity';
export function TeamIdentityLink({team,to}:{team:string;to:string}) {
 const t=teamIdentity(team);
 return <Link className="rp-team-identity" to={to} aria-label={`${t.city} ${t.name} (${team}) — página do time`}><Logo team={{...t,logoPlate:false}}/><span className="rp-team-name"><strong>{team}</strong><span>{t.city} {t.name}</span></span></Link>;
}
