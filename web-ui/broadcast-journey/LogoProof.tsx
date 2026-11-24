import { useState, type CSSProperties } from 'react';
import { Logo } from '../broadcast-experience/TeamLogo';
import { teamIdentities, teamIdentity } from '../broadcast-real/identity';
import './journey.css';
export default function Proof() {
  const [id, setId] = useState('DAL');
  const team = id === 'FAIL' ? { id: 'FAIL', logo: '/missing-logo-proof.png' } : teamIdentity(id);
  return <main className="logo-proof"><h1>32 times. Logos locais.</h1><p>Painel de evidência visual. Arquivos originais, sem recolorir ou espelhar; marcas dos respectivos titulares.</p><div className="logo-proof-grid">{Object.values(teamIdentities).map(t => <section key={t.id} style={{ '--team': t.color, '--team-dark': t.dark, '--optical': t.optical } as CSSProperties}><Logo team={t}/><h2>{t.id}</h2><p>{t.city} {t.name}</p></section>)}</div><section className="logo-proof-retry"><h2>Troca após falha real de imagem</h2><div data-testid="logo-retry"><Logo team={team}/><strong>{id}</strong></div><button onClick={() => setId('FAIL')}>Simular falha</button><button onClick={() => setId('IND')}>Trocar para IND</button><button onClick={() => setId('DAL')}>Restaurar DAL</button></section></main>;
}
