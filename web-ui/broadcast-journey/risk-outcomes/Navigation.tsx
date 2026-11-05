import {Link,useSearchParams} from 'react-router-dom';
import {href} from '../risk-lab/model';
export function ReadingNavigation(){const [q]=useSearchParams(),active=q.get('reading')==='interceptions'?'interceptions':'passes';return <nav className="ro-questions" aria-label="Pergunta do laboratório">{[
 ['passes','Risco dos passes','Mais passes interceptáveis do que o contexto sugeria?'],
 ['interceptions','Interceptações sofridas','Mais ou menos interceptações do que a referência esperava?']
].map(([key,title,question])=><Link key={key} to={href(q,{reading:key})} preventScrollReset aria-current={active===key?'page':undefined}><strong>{title}</strong><span>{question}</span></Link>)}</nav>;}
