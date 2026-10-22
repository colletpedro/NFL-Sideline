// Visual catalogue only. No fixtures, metrics or relation aliases.
import ari from '../broadcast-real/assets/ari.png';
import atl from '../broadcast-real/assets/atl.png';
import bal from '../local-editorial/broadcast/assets/bal.png';
import buf from '../broadcast-experience/assets/buf.png';
import car from '../broadcast-real/assets/car.png';
import chi from '../broadcast-experience/assets/chi.png';
import cin from '../broadcast-real/assets/cin.png';
import cle from '../broadcast-real/assets/cle.png';
import dal from '../local-editorial/broadcast/assets/dal.png';
import den from '../broadcast-real/assets/den.png';
import det from '../broadcast-real/assets/det.png';
import gb from '../broadcast-experience/assets/gb.png';
import hou from '../broadcast-real/assets/hou.png';
import ind from '../broadcast-real/assets/ind.png';
import jax from '../broadcast-real/assets/jax.png';
import kc from '../broadcast-experience/assets/kc.png';
import la from '../broadcast-real/assets/la.png';
import lac from '../broadcast-real/assets/lac.png';
import lv from '../broadcast-real/assets/lv.png';
import mia from '../broadcast-real/assets/mia.png';
import min from '../broadcast-real/assets/min.png';
import ne from '../local-editorial/broadcast/assets/ne.png';
import no from '../broadcast-real/assets/no.png';
import nyg from '../broadcast-real/assets/nyg.png';
import nyj from '../broadcast-real/assets/nyj.png';
import phi from '../broadcast-real/assets/phi.png';
import pit from '../broadcast-experience/assets/pit.png';
import sea from '../broadcast-real/assets/sea.png';
import sf from '../broadcast-real/assets/sf.png';
import tb from '../broadcast-real/assets/tb.png';
import ten from '../broadcast-real/assets/ten.png';
import was from '../broadcast-real/assets/was.png';
export interface TeamIdentity { id: string; city: string; name: string; logo: string; color: string; dark: string; optical: number; aliases?: string[]; logoPlate?: boolean }
export const teamIdentities: Record<string, TeamIdentity> = {
  ARI: { id: 'ARI', city: 'Arizona', name: 'Cardinals', logo: ari, color: '#87213D', dark: '#48182B', optical: 1, aliases: [] },
  ATL: { id: 'ATL', city: 'Atlanta', name: 'Falcons', logo: atl, color: '#952238', dark: '#481C28', optical: 1, aliases: [] },
  BAL: { id: 'BAL', city: 'Baltimore', name: 'Ravens', logo: bal, color: '#593D8A', dark: '#25153D', optical: 1.02, aliases: [] },
  BUF: { id: 'BUF', city: 'Buffalo', name: 'Bills', logo: buf, color: '#124B99', dark: '#102C56', optical: 1, aliases: [] },
  CAR: { id: 'CAR', city: 'Carolina', name: 'Panthers', logo: car, color: '#006A9F', dark: '#103746', optical: 1, aliases: [] },
  CHI: { id: 'CHI', city: 'Chicago', name: 'Bears', logo: chi, color: '#243E5B', dark: '#111F32', optical: 1, aliases: [] },
  CIN: { id: 'CIN', city: 'Cincinnati', name: 'Bengals', logo: cin, color: '#A73C16', dark: '#4D241A', optical: 1, aliases: [] },
  CLE: { id: 'CLE', city: 'Cleveland', name: 'Browns', logo: cle, color: '#78412A', dark: '#38251E', optical: 1, aliases: [] },
  DAL: { id: 'DAL', city: 'Dallas', name: 'Cowboys', logo: dal, color: '#2463A0', dark: '#0B3057', optical: 0.76, aliases: [] },
  DEN: { id: 'DEN', city: 'Denver', name: 'Broncos', logo: den, color: '#2A4B70', dark: '#142C49', optical: 1, aliases: [] },
  DET: { id: 'DET', city: 'Detroit', name: 'Lions', logo: det, color: '#006AA4', dark: '#153D59', optical: 1, aliases: [] },
  GB: { id: 'GB', city: 'Green Bay', name: 'Packers', logo: gb, color: '#245345', dark: '#152F29', optical: 1, aliases: [] },
  HOU: { id: 'HOU', city: 'Houston', name: 'Texans', logo: hou, color: '#234957', dark: '#102831', optical: 1, aliases: [] },
  IND: { id: 'IND', city: 'Indianapolis', name: 'Colts', logo: ind, color: '#17578A', dark: '#102E52', optical: 1, aliases: [] },
  JAX: { id: 'JAX', city: 'Jacksonville', name: 'Jaguars', logo: jax, color: '#086475', dark: '#163A40', optical: 1, aliases: [] },
  KC: { id: 'KC', city: 'Kansas City', name: 'Chiefs', logo: kc, color: '#A82037', dark: '#5A1728', optical: 1, aliases: [] },
  LA: { logoPlate: true, id: 'LA', city: 'Los Angeles', name: 'Rams', logo: la, color: '#2453A0', dark: '#163467', optical: 1, aliases: ["LAR"] },
  LAC: { id: 'LAC', city: 'Los Angeles', name: 'Chargers', logo: lac, color: '#006BA3', dark: '#153C58', optical: 1, aliases: [] },
  LV: { id: 'LV', city: 'Las Vegas', name: 'Raiders', logo: lv, color: '#46525C', dark: '#222C34', optical: 1, aliases: [] },
  MIA: { id: 'MIA', city: 'Miami', name: 'Dolphins', logo: mia, color: '#006B71', dark: '#164247', optical: 1, aliases: [] },
  MIN: { id: 'MIN', city: 'Minnesota', name: 'Vikings', logo: min, color: '#604187', dark: '#34274D', optical: 1, aliases: [] },
  NE: { id: 'NE', city: 'New England', name: 'Patriots', logo: ne, color: '#C90827', dark: '#870016', optical: 1.1, aliases: [] },
  NO: { id: 'NO', city: 'New Orleans', name: 'Saints', logo: no, color: '#63573C', dark: '#353126', optical: 1, aliases: [] },
  NYG: { logoPlate: true, id: 'NYG', city: 'New York', name: 'Giants', logo: nyg, color: '#294A8A', dark: '#1A2E52', optical: 1, aliases: [] },
  NYJ: { logoPlate: true, id: 'NYJ', city: 'New York', name: 'Jets', logo: nyj, color: '#245841', dark: '#18392C', optical: 1, aliases: [] },
  PHI: { id: 'PHI', city: 'Philadelphia', name: 'Eagles', logo: phi, color: '#12616A', dark: '#173C42', optical: 1, aliases: [] },
  PIT: { id: 'PIT', city: 'Pittsburgh', name: 'Steelers', logo: pit, color: '#55503C', dark: '#2D2E28', optical: 1, aliases: [] },
  SEA: { id: 'SEA', city: 'Seattle', name: 'Seahawks', logo: sea, color: '#27485D', dark: '#172E40', optical: 1, aliases: [] },
  SF: { id: 'SF', city: 'San Francisco', name: '49ers', logo: sf, color: '#A72B32', dark: '#571E27', optical: 1, aliases: [] },
  TB: { id: 'TB', city: 'Tampa Bay', name: 'Buccaneers', logo: tb, color: '#A42C31', dark: '#54272B', optical: 1, aliases: [] },
  TEN: { id: 'TEN', city: 'Tennessee', name: 'Titans', logo: ten, color: '#275D86', dark: '#16364F', optical: 1, aliases: [] },
  WAS: { id: 'WAS', city: 'Washington', name: 'Commanders', logo: was, color: '#782E3C', dark: '#431E29', optical: 1, aliases: ["WSH"] },
};
export const teamIdentity = (id: string): TeamIdentity => teamIdentities[id] ?? { id, city: id, name: id, logo: '', color: '#3E5360', dark: '#243640', optical: 1 };
