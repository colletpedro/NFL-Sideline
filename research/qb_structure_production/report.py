"""Render review documents and small support tables from the immutable research package."""
import argparse,shutil
from common import *

def table(d,cols=None):
 if cols:d=d[cols]
 def fmt(x):
  if pd.isna(x):return '—'
  if isinstance(x,(float,np.floating)):return f'{x:.3f}'
  return str(x).replace('|',' / ').replace('\n',' ')
 return '| '+' | '.join(d.columns)+' |\n| '+' | '.join(['---']*len(d.columns))+' |\n'+'\n'.join('| '+' | '.join(fmt(x) for x in row)+' |' for row in d.itertuples(index=False,name=None))+'\n'

def render(p,out,s):
 p=Path(p);out=Path(out);s=Path(s);d=pd.read_parquet(p/'plays.parquet');main=d[d.season.ge(2023)];c=pd.read_csv(p/'comparisons.csv');l=pd.read_csv(p/'league.csv');cases=read(p/'examples/index.json');audit=read(p/'audit/raw.json');cur=int(main.season.max());q=c[c.position_class.eq('qb')];lc=l[l.season.eq(cur)].set_index('category');cross=pd.read_csv(p/'audit/classified_cross.csv')
 for sub in ['figures','tables','evidence']:(out/sub).mkdir(exist_ok=True)
 for src in (p/'figures').iterdir():shutil.copyfile(src,out/'figures'/src.name)
 for name in ['categories.csv','comparisons.csv','league.csv','context_bins.csv','context_summary.csv','stability.csv','extreme_diagnostics.csv','group_extremes.csv']:
  shutil.copyfile(p/name,out/'tables'/name)
 for name in ['sources.json','parent-sources.json']:shutil.copyfile(s/name,out/'evidence'/name)
 for name in ['index.json','manifest.json','fixed.json','coverage.json']:shutil.copyfile(p/name,out/'evidence'/('package-'+name))
 for src in (p/'audit').glob('*.csv'):shutil.copyfile(src,out/'tables'/src.name)
 for src in (p/'examples').glob('*extremes.csv'):shutil.copyfile(src,out/'tables'/src.name)
 write(out/'evidence/examples.json',cases)
 pop=[]
 for y,g in main.groupby('season'):
  pop.append(dict(temporada=y,dropbacks=len(g),lançamentos=int(g.event_type.eq('pass').sum()),sacks_PBP=int(g.sack.eq(1).sum()),scrambles_PBP=int(g.qb_scramble.eq(1).sum()),jogos=g.game_id.nunique(),dropbacks_QB=int(g.position_class.eq('qb').sum()),dropbacks_outras_posições=int(g.position_class.eq('other').sum()),FTN_ausente=int((~g.charting_present).sum()),EPA_ausente=int(g.epa.isna().sum())))
 pop=pd.DataFrame(pop);pop.to_csv(out/'tables/population.csv',index=False)
 leagues=[];flips=[]
 for y,g in l.groupby('season'):
  a=g[g.category.eq('progression')].iloc[0]
  for version,cats in GROUPS.items():
   b=g[g.category.isin(cats)];bm=b.sum_epa.sum()/b.n_epa.sum();leagues.append(dict(temporada=y,definição=version,n_A=a.n,media_A=a.mean_epa,n_B=int(b.n.sum()),media_B=bm,diferença=a.mean_epa-bm))
  cohort=q[q.season.eq(y)&q.definition.eq('main')&q.status.eq('legible')]
  for version in ['S1','S2','S3']:
   j=cohort.merge(q[q.season.eq(y)&q.definition.eq(version)],on='player_id',suffixes=('_m','_s'));flips.append(dict(temporada=y,definição=version,coorte_principal=len(j),mudam_sinal=int((j.difference_m*j.difference_s<0).sum()),B_abaixo_corte=int(j.status_s.ne('legible').sum())))
 leagues=pd.DataFrame(leagues);leagues.to_csv(out/'tables/league_comparisons.csv',index=False);flips=pd.DataFrame(flips);flips.to_csv(out/'tables/sign_sensitivity.csv',index=False)
 selected=[]
 for case in cases:
  r=case['selection'];selected.append(dict(critério=case['criterion'],jogador=r['audited_name'],GSIS=r['player_id'],n_A=r['a_n_epa'],EPA_A=r['a_mean'],n_B=r['b_n_epa'],EPA_B=r['b_mean'],diferença=r['difference'],frequência_B=r['b_pct_all'],status=r['status']))
 selected=pd.DataFrame(selected);selected.to_csv(out/'tables/examples.csv',index=False)
 stat=pd.read_csv(p/'stability.csv');stat=stat[stat.field.isin(['a_mean','b_mean','difference','b_pct_all'])]
 ctx=pd.read_csv(p/'context_summary.csv');ctx=ctx[ctx.season.eq(cur)]
 cp=main.groupby(['season','category']).size().unstack(fill_value=0).reindex(columns=CATS);cp.reset_index().to_csv(out/'tables/category_counts_all_positions.csv',index=False)
 current_cat=main[main.season.eq(cur)].groupby('category').agg(n=('play_id','size'),n_epa=('epa','count'),sum_epa=('epa','sum'),mean_epa=('epa','mean')).reindex(CATS).reset_index();current_cat['pct_all']=100*current_cat.n/current_cat.n.sum()
 intro='''# Produção dos quarterbacks na progressão e em improvisação

**Entrega de pesquisa v1.0.0 · 05/11/2026 · sem integração ou publicação.** A comparação operacional é utilizável, mas **sensível à definição**. Ela mede a produção observada em passes com progressão registrada e em passes SD + scrambles verificados de QB. Não mede uma partição perfeita de todos os dropbacks dentro/fora da estrutura, nem dependência causal da estrutura ofensiva.

A principal evidência é que incluir scrambles, throwaways e sacks muda substancialmente a leitura. Em 2026, a média ponderada dos QB é **0,230 EPA/jogada em A** e **0,309 em B**. Só passes SD produzem **0,163**; com throwaways B cai para **0,009**; com throwaways e sacks, para **−0,519**. Não há justificativa para escolher apenas a definição que sustenta uma narrativa sobre um jogador.

## População e procedência

'''
 report=intro+table(pop)+'''
A comparação principal contém 69.505 dropbacks de 2023–2026. Há 20.210 dropbacks de 2022 em auditoria separada; nenhuma média ou correlação principal inclui 2022. O recorte atual contém 121 jogos REG encerrados, W1–8, até 02/11/2026; 151 jogos futuros e zero jogos encerrados pendentes no gate de encerramento. Sem espera por semana completa. Fontes próprias copiadas após conferir os 27 hashes do manifest XINT; nenhum cache derivado de passes foi usado como universo.

Todas as jogadas elegíveis encontram FTN e EPA finito nestas fontes. Em 2026 são 57 QB com 8.951 dropbacks e 11 outros participantes com 11 jogadas, mantidos nas tabelas; os 435 eventos PBP de scramble incluem um WR, que fica no residual, com identidade preservada. Sacks PBP são 557, um deles de WR; a referência da liga usa 556 sacks de QB. Os totais brutos reproduzem as pistas iniciais, mas as categorias finais diferem por regras explícitas. [Auditoria](DATA-AUDIT.md) · [fontes/hashes](evidence/sources.json) · [cobertura por jogo](evidence/package-coverage.json).

## Categorias e cobertura da comparação

A classificação aplica checagem de corrupção/aborto e depois sack → scramble verificado → throwaway em lançamento → passe SD → leitura registrada (`0,1,2,CHK`) → residual. Indicadores originais permanecem; um throwaway com código de leitura não vira passe de progressão. `DES` não representa uma progressão: é lançamento desenhado sem progressão e permanece como subtipo conhecido do residual. [Contrato congelado](RESEARCH-CONTRACT.md) · [regras completas](CLASSIFICATION.md).

Em 2026, todos os participantes:

'''+table(current_cat)+'''
O residual de 799 jogadas contém 797 `DES`, um aborto e um scramble de WR. Logo, 8,92% de residual **não significa** 8,92% de charting ausente. Nos QB são 791/8.951 = 8,84% residuais, dos quais 790 `DES` e um aborto. A+B dos QB cobre 7.249/8.951 = 80,99%; outros blocos continuam visíveis. Não esconder o residual usando somente o denominador classificável.

![Categorias](figures/01_distribution.png)

## Produção principal e sensibilidades

Médias da liga são ponderadas por jogadas de QB verificados, usando toda a população elegível da temporada, inclusive QB com pouco suporte individual. A figura principal mostra somente o corte de legibilidade congelado: ≥100 EPA válidos em A, ≥25 em B e ≥5 jogos com A/B. Em 2026 passam 15 dos 57 QB; 37 têm pouco suporte e cinco não têm oportunidades em pelo menos um dos lados. Isso não garante robustez; as tabelas completas conservam todos os participantes e zeros de oportunidade como indisponíveis.

'''+table(leagues[leagues['definição'].eq('main')])+'''
A diferença é **média A − média B**. Positivo significa maior produção observada em A. Uma diferença alta pode vir de A excepcional; sempre mostrar os dois níveis e volumes. Não concluir incapacidade de improvisar. A diagonal do scatter indica diferença zero, sem interpretação de desempenho ideal. As referências de liga são médias condicionais de populações diferentes de jogadas, não uma comparação pareada de oportunidades equivalentes.

![Produção nas duas condições](figures/02_progression_vs_improvisation.png)

![Frequência e produção](figures/03_frequency_vs_production.png)

Em 2026, a frequência B dos QB é 909/8.951 = 10,16%, formada por 475 passes SD (5,31%) e 434 scrambles (4,85%). Scrambles somam 203,095 EPA e os passes SD 77,501. Assim, 47,7% dos eventos de B fornecem 72,4% de sua soma de EPA. É parte substantiva da definição, não um detalhe descartável.

'''+table(leagues[leagues.temporada.eq(cur)])+'''
S1 acrescenta descarte sem afirmar que todo throwaway decorreu de quebra de estrutura. S2 acrescenta todos os sacks como hipótese ampliada; não identifica em qual momento cada sack ocorreu. S3 retira scrambles e compara só lançamentos. Todas as versões mantêm A fixo e são reconstruídas das seis categorias.

No conjunto dos 15 QB legíveis de 2026, S1 muda o sinal de seis diferenças; S2 muda dez; S3 muda três, mas **14 dos 15 ficam abaixo de 25 passes SD**. Não tratar S3 como ranking igualmente sustentado. Nos anos completos, S2 muda o sinal em 24/34 (2023), 23/33 (2024) e 21/32 (2025). [Tabela completa das inversões](tables/sign_sensitivity.csv).

![Sensibilidade](figures/04_sensitivity.png)

## História, composição e extremos

As quatro temporadas são mostradas separadamente; não há agregado histórico que misture calendários ou esconda 2026 parcial. Pares adjacentes exigem o mesmo suporte em ambos os anos:

'''+table(stat[['season','next_season','field','n_pairs','pearson','spearman']])+'''
A frequência B apresenta correlações maiores que a diferença de produção em todos os pares. A diferença tem Pearson 0,039; 0,024; −0,113. Os níveis A/B variam de modo desigual: não há uma medida de habilidade persistente estabelecida por essas correlações. Mesmo a correlação da frequência pode refletir desenho ofensivo, utilização, adversários e estabilidade da anotação. São populações de jogadores selecionadas por volume, com 2026 parcial.

A proporção de scrambles PBP marcada SD muda de 252/1.035 (24,35%) em 2023 e 293/1.062 (27,59%) em 2024 para 962/1.089 (88,34%) em 2025 e 415/435 (95,40%) em 2026. A regra fixa de scramble usa PBP e roster, portanto não depende desse SD; isso não certifica estabilidade completa do charting de passes SD. Não interpretar `read_thrown` em corridas/sacks como leitura lançada.

![Temporadas separadas](figures/05_historical.png)

O contexto de B já difere de A: em 2026, terceiras/quartas descidas são 38,94% de B e 29,53% de A; primeiras são 28,82% versus 37,15%. Distância média: 8,79 versus 8,92 jardas; distância média até a end zone adversária: 48,39 versus 51,11; placar pré-jogada: −2,99 versus −2,94. B aparece um pouco mais no Q4 (29,04% versus 27,97%). As distribuições por descida, distância, campo, quarto, relógio e placar de **cada ano** estão em [faixas](tables/context_bins.csv) e [médias/medianas](tables/context_summary.csv). Isso não iguala proteção, defesa, recebedores ou alternativas não observadas. Nenhuma regressão foi adicionada.

A métrica principal conserva todos os EPA, inclusive extremos. Como diagnóstico, subtrair os cinco maiores |EPA| **de cada lado** faria a diferença de Stroud passar de −0,405 para +0,018, Willis de +0,005 para +0,104 e Mahomes de +0,392 para +0,231; em Maye permanece negativa (−0,670 → −0,330). Esse exercício não é uma estimativa corrigida nem uma forma de estabilizar ordenação: muda o universo e evidencia concentração. Os cinco eventos de maior |EPA| de B concentram 39,5% da soma absoluta em Stroud, 27,2% em Maye e 90,3% em Stafford. [Todos os diagnósticos e somas assinadas](tables/group_extremes.csv).

## Exemplos selecionados sem nomes

Os critérios foram congelados antes das comparações: maior diferença com A acima da liga; maior nível B; menor diferença absoluta; maior deslocamento S2; menor B positivo com A≥100 e B<25. Desempate por GSIS; não houve substituição posterior para confirmar o vídeo.

'''+table(selected)+'''
Mahomes combina A acima da liga com B próximo de zero neste recorte; isso não mede dependência causal. Maye tem maior B entre os elegíveis, e a diferença troca de sinal em S2. Willis fica próximo de zero na principal, embora S3 dê diferença +0,737 com só 20 passes SD. Stroud é o caso mais sensível a S2: −0,405 → +0,635; já S1 muda para +0,037. Seus 15 sacks somam −28,445 EPA; de S1 para S2, B cai de +0,258 para −0,340 EPA/jogada. Stafford tem só sete eventos B (três SD e quatro scrambles), volume inadequado para a figura principal, apesar de 265 A.

'''
 for case in cases:
  r=case['selection'];pid=r['player_id'];g=main[main.season.eq(cur)&main.player_id.eq(pid)];rows=[]
  for cat,part in g.groupby('category'):
   e=part.assign(abs_epa=part.epa.abs()).sort_values(['abs_epa','game_id','play_id'],ascending=[False,True,True]).iloc[0]
   rows.append(dict(categoria=cat,jogo=e.game_id,jogada=int(e.play_id),regra=e.rule,descida=e.down,distância=e.ydstogo,quarto=e.qtr,relógio=e.time,campo=e.yrdln,EPA=e.epa))
  report+=f"### {r['audited_name']} · {pid}\n\n"+table(pd.DataFrame(rows))+f"\nUma jogada por categoria, escolhida por maior |EPA|, somente para localizar contribuições. [Todas as {len(g)} jogadas e descrições da fonte](<{p/case['all_plays']}>) · [12 extremos com descrição literal](tables/{case['criterion']}_extremes.csv). As regras e evidências brutas constam em cada linha. Não inferir intenção ou culpa a partir do texto.\n\n"
 report+='''## Limites e recomendação de apresentação

EPA é o `epa` da jogada PBP: produção do ataque, com contribuição de recebedores/YAC, adversários, proteção e penalidades válidas. Não isola o QB; `qb_epa`, WPA ou resultado de vitória não foram substitutos. Charting FTN é retrospectivo e revisável; `date_pulled` não comprova anotação cega. Não há medida completa de pressão; qb_hit, blitzers e saída do pocket não foram usados como tal. O pocket pode ser abandonado por desenho, e segunda/terceira leitura podem ocorrer dentro da estrutura. Não identificamos alternativas não escolhidas.

Não foram produzidos intervalos nesta versão. Volumes pequenos, heterogeneidade e definição operacional permanecem limitações; o corte não é certificação estatística. Uma futura reamostragem teria de selecionar jogos conjuntamente para A/B e reportar réplicas sem oportunidades em um lado. Não tratar os grupos como amostras independentes.

**Recomendação:** revisar este pacote como leitura experimental de “produção em progressão registrada e improvisação identificada”. Na futura integração, mostrar níveis A/B, composição de todos os dropbacks, volumes, residual separado por motivo, toggle das quatro definições e acesso às jogadas. Sacks/throwaways merecem blocos próprios. Evitar ranking de dependência do sistema, quadrantes valorativos e tradução automática em qualidade individual. Preservar M3/B2 como perguntas distintas. Nenhuma conexão à interface foi feita.

[Reprodução e atualização](README.md) · [cartão da métrica](METRIC-CARD.md) · [passagem de integração](HANDOFF.md) · [verificação independente](evidence/independent-reconciliation-final.json).
'''
 (out/'REPORT.md').write_text(report)
 auditmd='''# Auditoria de fontes e classificação

Leitura independente dos PBP/FTN brutos, sem limitar ao dataset de tentativas do XINT. [Manifest das cópias próprias](evidence/sources.json) conserva URLs, instantes de aquisição originais, tamanhos, SHA-256, atribuição/licença e hash do manifest pai. Os 27 arquivos do pai foram conferidos antes da cópia; as 20 fontes necessárias desta pesquisa foram copiadas, sem substituir revisões pinadas ou baixar dados novos. [Manifest pai](evidence/parent-sources.json).

## Universo, cobertura e reconciliação

'''+table(pop)+'''
Cada chave PBP/FTN é única e não nula. Duplicata, mesmo idêntica, aborta; não se escolhe cache arbitrariamente. Zero FTN órfão de PBP nas cinco fontes. Os funis, nulls, penalidades, overtime, abortos e códigos brutos estão em `package-release/audit/raw.json`; excluídas conservadas por ano em Parquet fora do Git. Penalidades entram somente quando PBP conserva evento pass/run elegível; no_play, deleted, spikes, kneels e conversões não passam. Não filtramos por sinal de EPA ou pessoa.

2026: 7.970 lançamentos + 557 sacks + 435 scrambles = 8.962 dropbacks. 2023–2026: 69.505. A pista inicial é reconciliada no universo bruto, não usada como meta. As diferenças nas categorias vêm de DES, aborto, flags contraditórias e posição auditada. Nenhuma diferença foi corrigida por imputação.

A segunda implementação usa **SQLite sobre os arquivos brutos**, com filtro, LEFT JOIN FTN, join roster, CASE de classificação e soma/média por GSIS/categoria. Não importa o classificador nem o agrupador principal. Comparou todas as chaves, identidades, categorias, EPA e 1.643 agregados não vazios de 2023–2026; contagens exatas e somas/médias com tolerância absoluta 1e−10. Também reconcilia 20.210 linhas em 2022. [Recibo final](evidence/independent-reconciliation-final.json). Verificador adicional reconstrói todas as sensibilidades, sinal, somas e denominadores por jogador.

## Dicionários e significado

[Dicionário FTN](https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html): 0 primeira; 1 segunda; 2 terceira ou posterior; CHK checkdown; DES lançamento desenhado sem progressão; SD lançamento após quebra da jogada. O documento explicita diferença de 2022, quando 0 ainda não é utilizado. [Loader FTN](https://nflreadr.nflverse.com/reference/load_ftn_charting.html): charting manual, FTN Data via nflverse, CC BY-SA 4.0. [Dicionário PBP](https://nflreadr.nflverse.com/articles/dictionary_pbp.html) e [CSV oficial pinado](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv): qb_dropback inclui lançamento/sack/scramble; pass_attempt inclui sacks; run inclui scrambles; epa é EPA do ataque na jogada. Não tratamos pass_attempt como lançamento executado.

As cópias exatas dos dicionários/licença estão em `sources/documentation/`, hash no manifest. A consulta atual à documentação oficial concordou com a cópia pinada sobre estes campos. Não reclassificar anos silenciosamente com base em uma nomenclatura moderna. [Cruzamento dos brutos, incluindo excluídas](tables/raw_cross_2026.csv) e os equivalentes 2022–2025 mostram códigos em corridas/sacks; não são leituras lançadas nesses eventos.

## Códigos, cruzamentos e sobreposições

'''
 readcounts=main[main.event_type.eq('pass')].groupby(['season','read_normalized'],dropna=False).size().unstack(fill_value=0).reset_index();auditmd+=table(readcounts)
 auditmd+='''
Em 2022 são 379 lançamentos sem leitura e nenhum código 0, além de uma string com whitespace ` CHK` no bruto FTN. A normalização conserva original e aplica strip/uppercase, sem converter NA em primeira leitura. Os códigos em todos os eventos têm composição diferente dos lançamentos: não assumir estabilidade só pela presença da coluna. A comparação agrupa as leituras conhecidas e não tenta distinguir primária/segunda por inferência própria.

Scrambles PBP com SD: 7/905 em 2022; 252/1.035 em 2023; 293/1.062 em 2024; 962/1.089 em 2025; 415/435 em 2026. O comportamento muda fortemente. Sacks também podem carregar códigos registrados; a precedência conserva esses códigos como evidência secundária e classifica o evento sack. [Cruzamento elegível completo](tables/classified_cross.csv) inclui ano, valor bruto/normalizado, tipo de evento, categoria, throwaway e saída do pocket. [Flags desenhadas](tables/designed_flags.csv) incluem screen, RPO, play action, trick e sneak; não substituem uma anotação geral de rollout/run desenhado, indisponível nestas fontes.

2026: 355 throwaways. Destes, 192 carregam 0/1/2/CHK, 19 DES e 144 SD. Portanto a pista de 211 com código de leitura se decompõe em 192 de progressão registrada + 19 DES; não são 211 passes de A. Outros códigos não foram apagados. [Motivos por ano](tables/reasons.csv) expõe dois throwaways sem lançamento em 2023, dois throwaways completos/interceptados em 2024 e dois em 2022, além de abortos. Estes conflitos ficam no residual, sem resolver pelo EPA. Não houve código desconhecido após normalização; todos os lançamentos de 2023–2026 têm leitura bruta preenchida. Flags fora do domínio binário seriam residuais; ausência nunca vira false.

## Identidade e posições

GSIS no PBP, roster semanal na mesma temporada/semana/time, aliases documentados. Scramble usa rusher somente após verificar evento run + scramble, flags de passe/sack e concordância com passer se presente. Todos os scrambles têm passer ausente nas fontes; roster resolve seus rushers. Há 11 eventos 2022–2026 de rusher não-QB, todos WR: 3/3/2/2/1 por ano. Conservam GSIS/nome/posição, mas não entram no grupo B de QB; ficam em `scramble_non_qb_position`. Não são identidades desconhecidas. Nenhum GSIS desta aquisição ficou sem resolução após esse esclarecimento. [Tabela por identidade/equipe](tables/identity.csv).

Em 2026 há nove lançamentos de outras posições, um sack de WR e um scramble de WR; nenhum é removido do universo. Trocas de equipe agrupam pelo mesmo GSIS, com equipes no agregado. A unidade não é jogador+time. A primeira implementação de desenvolvimento agrupou os scrambles WR como identidade não resolvida; a correção preserva os GSIS conhecidos e não altera nenhum resultado de QB. Saídas intermediárias permanecem no store, sem consumo ativo.

## EPA, contexto e licença

Zero EPA ausente/infinto nas elegíveis destas revisões. O código mantém n de eventos separado de n EPA e deixa média/soma indisponíveis sem EPA, com testes sintéticos. Nenhuma imputação. Contexto pré-jogada tem distribuições e ausências explícitas nas tabelas; descrição é evidência de inspeção, não entrada de classificação. `qb_hit`, `n_blitzers` e fora do pocket não são medidas de pressão efetiva aqui.

FTN Data via nflverse: dados transformados sob CC BY-SA 4.0, sem endosso. PBP/roster/schedule: nflverse-data CC BY 4.0 com escopo subjacente não certificado juridicamente, licença pinada no store. Não houve publicação externa. Charting/EPA e fontes podem sofrer revisões; não temos o histórico completo do provedor. Atualização é uma nova aquisição imutável, com diferenças por chave/campo e sem ativação automática.
'''
 (out/'DATA-AUDIT.md').write_text(auditmd)
 print('Documents rendered',out)

if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('--package',required=True);a.add_argument('--out',required=True);a.add_argument('--sources',required=True);v=a.parse_args();render(v.package,v.out,v.sources)
