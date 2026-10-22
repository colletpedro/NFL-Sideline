import dal from '../local-editorial/broadcast/assets/dal.png';
import ne from '../local-editorial/broadcast/assets/ne.png';
import bal from '../local-editorial/broadcast/assets/bal.png';
// Brand metadata only, copied from the accepted visual reference. Never metrics.
const teams = {
  DAL: { id: 'DAL', city: 'Dallas', name: 'Cowboys', logo: dal, color: '#2463A0', dark: '#0B3057', optical: .76 },
  NE: { id: 'NE', city: 'New England', name: 'Patriots', logo: ne, color: '#C90827', dark: '#870016', optical: 1.1 },
  BAL: { id: 'BAL', city: 'Baltimore', name: 'Ravens', logo: bal, color: '#593D8A', dark: '#25153D', optical: 1.02 },
};
export const teamIdentity = (id: string) => teams[id as keyof typeof teams] ?? { id, city: id, name: id, logo: '', color: '#3E5360', dark: '#243640', optical: 1 };
