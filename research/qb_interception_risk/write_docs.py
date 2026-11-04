"""Build readable Portuguese research documents from frozen evidence (offline)."""
from pathlib import Path
import argparse,json
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent

def table(headers,rows):
 return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(str(v) for v in row)+' |\n' for row in rows)
def write_docs(store,doc):
 s=Path(store);doc=Path(doc);a=json.loads((s/'build-v2/audit.json').read_text());m=json.loads((s/'evaluation-v1/metrics.json').read_text());dev=json.loads((s/'development-v3/development_metrics.json').read_text());q=pd.read_csv(s/'application-v1/qb_context.csv');sens=pd.read_csv(s/'application-v1/qb_sensitivity.csv');cal=json.loads((s/'evaluation-v1/calibration_context.json').read_text());dis=pd.read_csv(s/'build-v2/audit/feature_distributions.csv');groups=json.loads((s/'evaluation-v1/groups_context.json').read_text())
 def put(name,text):(doc/name).write_text(text.strip()+'\n')
 counts=table(['Temporada','Jogos REG','Passes elegíveis','Interceptáveis FTN','Taxa','INT'],[[y,v['coverage']['reg_games'],v['target']['n'],v['target']['worthy'],f"{100*v['target']['prevalence']:.3f}%",v['target']['interceptions']] for y,v in a.items()])
 funnel=table(['Etapa (remanescente)','2022','2023','2024','2025','2026 W1–7'],[[a['2022']['funnel'][i]['stage']]+[a[y]['funnel'][i]['remaining'] for y in a] for i in range(len(a['2022']['funnel']))])
 crosses=table(['Ano','Não interceptável / não INT','Não interceptável / INT','Interceptável / não INT','Interceptável / INT'],[[y,v['cross']['0.0']['0'],v['cross']['1.0']['0'],v['cross']['0.0']['1'],v['cross']['1.0']['1']] for y,v in a.items()])
 put('DATA-AUDIT.md',f'''# Auditoria de dados — gate PASS para pesquisa retrospectiva local

{counts}

Total: **78.460 passes**, dos quais 71.354 históricos (2022–25) e 7.106 na aplicação. 2023, 2025 e 2026 reproduzem as pistas fornecidas (18.248/738/430; 17.358/553/380; 7.106/219/146). Nenhuma regra foi ajustada para obter esses números.

## Fontes e congelamento

Aquisição em 04/11/2026, instantes UTC por arquivo no [manifesto](evidence/sources.json). PBP2022–25: cópias próprias dos assets oficiais `play_by_play_YEAR.parquet`, sem usar o cache de procedência não comprovada. FTN2022–26: assets `ftn_charting_YEAR.parquet`. PBP2026: cópia byte a byte da fonte aprovada de 27/10, SHA-256 `7a5f4fa5b933b24474d8a5a8c76e57b23b8b50b7e62950ab1e5c9ea00cbf4507`, 107 jogos/18.738 linhas. Nunca foi substituído pelo PBP2026 remoto ou pelo cache W1–2. Schedules nfldata também pinados para confrontar o universo de jogos. Esquemas Arrow completos, metadados Parquet, tamanho, hash, URL, instante e cobertura por arquivo no manifesto. Ambiente de aquisição inicial e ambiente final têm locks preservados; mudança numérica documentada no checkpoint.

Armazenamento durável: `{s}`. `raw/` contém fontes; `build-v2/` contém dataset, splits e auditorias; `development-v3/` contém freeze pré-teste e modelos; `evaluation-v1/` teste; `application-v1/` aplicação; `figures-v4/` gráficos finais; `wheelhouse/` dependências. Não há binários brutos versionados no Git. O manifesto não torna um checkout novo autossuficiente: é preciso restaurar essas fontes ou adquiri-las em um store novo, que poderá conter revisões diferentes.

## Funil explícito

{funnel}

Os filtros são sequenciais, portanto zero em uma etapa pode significar que os casos já saíram antes. `pass_type` retira corridas/scrambles, spikes classificados como tal, special teams, `no_play` e marcadores administrativos; sacks saem depois. Conversões de dois pontos saem mesmo quando `play_type=pass`. Flags desconhecidas não viram zero. Não usamos um `dropna` geral: identidade e cobertura de alvo são etapas explícitas. As features principais não têm ausências entre os elegíveis.

## Penalidades e casos especiais

Penalidades com tentativa mantida pelo PBP permanecem: 225/241/230/251/107 por ano. Não se aplica `penalty==0`. Jogadas `no_play` ficam fora mesmo que FTN tenha charting: há respectivamente 67/34/32/25/19 rótulos positivos em `no_play` REG nos brutos; incluem interferência, holding, offside e outros. Em 2026 são 19 fora do universo, não rótulos elegíveis perdidos. Flags/descrições desses casos foram conservadas localmente em `build-v2/audit/no_play_worthy_YEAR.csv`; as listas de penalidades e tentativas revisadas também ficam em CSV. Não reinterpretamos descrição para salvar/descontar tentativa. Uma linha positiva fora de `no_play`/pass_type em 2022 é outra classificação não elegível; seis sacks em 2022 e quatro em 2023 também têm rótulo positivo. Isso mostra que o alvo bruto não deve ser somado sem população definida.

Throwaways mantidos: 684/744/701/722/318. Incompletos mantidos: 5.985/6.010/5.724/5.761/2.379. Receiver desconhecido: 702/765/727/749/302, sem exclusão. Overtime: 163/84/78/101/71 passes. `aborted_play` aparece em 0/1/2/0/1 elegíveis: uma tentativa após fumble recuperado e três descrições com decisão de replay que termina em passe incompleto; mantidos pela classificação final. Não é correto excluir automaticamente toda flag aborted. Não usamos receiver ou a decisão de replay como feature.

## Cardinalidade e reconciliação independente

Zero chaves nulas, zero duplicatas (até idênticas seriam recusadas) nos dois lados de todas as temporadas. Join validado 1:1 em `(game_id, play_id)` e metadados temporada/semana coerentes. Todos os elegíveis encontram rótulo binário não nulo; nenhum passer ausente. Regra futura: rótulo ausente aborta o gate, nunca False. Correção de fonte exige novo congelamento, não escolher uma duplicata arbitrária.

Na junção de todas as linhas, FTN2022 tem 41.643 correspondências e o PBP 7.791 linhas sem charting; 2023–25 têm respectivamente 48.225/48.031/47.316 correspondências e 1.440/1.461/1.455 linhas PBP sem charting. São fora da população elegível, não perda escondida. FTN2026 tem 18.191 matches no PBP aprovado e 2.381 linhas de 14 jogos W8 ausentes do PBP W1–7, além de 547 linhas PBP sem charting; os 2.381 registros W8 não eram esperados no join da aplicação e foram excluídos pela janela/conjunto de chaves. Mapas de razões e rótulos externos no JSON e Parquets `outside_eligible_YEAR`.

SQLite carregou diretamente os dois brutos, implementou WHERE/JOIN/GROUP BY próprio (sem chamar os filtros pandas), reconstruiu e comparou **cada chave, alvo e INT**, mais contagens/somas por temporada, semana, jogo e GSIS passer. Tudo exato em cinco temporadas. O score pré-jogada foi confrontado com `posteam_score - defteam_score`. [Auditoria completa](evidence/data-audit.json), [semanas](evidence/counts_by_week.csv), [jogos](evidence/counts_by_game.csv), [passers](evidence/counts_by_qb.csv).

O schedule pinado e o PBP compartilham exatamente os 271 jogos REG de 2022, 272 por ano em 2023–25 e 107 em 2026 W1–7. Não apareceu jogo esperado pelo schedule sem PBP. Isso não certifica todas as jogadas de cada partida, nem disponibilidade histórica ou precisão do charting. A menor cobertura FTN de linhas fora de passes em 2022 permanece característica da fonte, sem imputação.

## Alvo versus INT observada

{crosses}

INT não implica automaticamente rótulo FTN positivo (23 INT em 2026 são negativas no charting). O modelo usa FTN como alvo e mantém INT separada, sem segunda regressão ou interpretação de sorte.

## Identidade e estabilidade histórica

Agregação exclusivamente pelo GSIS `passer_player_id`; abreviações e times são exibição. Há colisões reais de abreviação: `J.Daniels` e `K.Allen` representam mais de um ID no histórico. Em 2026 dois `J.Daniels` são mantidos separados (WAS e TB). Trocas de equipe aparecem em 2022 `00-0034855`, 2023 `00-0033949`, 2024 `00-0034177`, 2025 `00-0026158`; não criam dois indivíduos. [Mapa completo](evidence/identities.csv).

A população contém todos os lançadores elegíveis, incluindo jogadores ocasionais de outras posições. Há **62 IDs**, e não afirmamos que sejam 62 QBs de roster: posição não foi certificada por fonte de roster. Todos os QBs com suporte estão no conjunto maior; 32 IDs têm pelo menos 100 passes. A tabela completa evita uma exclusão silenciosa de reservas ou trick plays.

`read_thrown` muda estruturalmente: primárias de 2022 são NA, código 0 só desde 2023; em 2022 há ainda um valor ` CHK` com espaço. Frequências brutas e elegíveis preservadas, sem recodificação nem uso como feature. A queda do rótulo 5,23% → 4,04% → 3,33% → 3,19% → 3,08% não foi explicada como mudança real de comportamento. Dicionário consultado não prova estabilidade de avaliadores/critério entre anos. `date_pulled` é metadado da fonte revisada, não certificado de disponibilidade histórica de cada jogada.

[Licença e atribuição](NOTICE.md). Completude do join ≠ completude da fonte ≠ verdade do rótulo.
''')
 feature_rows=[['down','Descida antes do snap','Categórica one-hot; moda só no treino'],['qtr','Quarto; 5=OT','Categórica one-hot; moda só no treino'],['ydstogo','Jardas até first down/endzone','Contínua + log1p'],['yardline_100','Distância até endzone adversária','Contínua + max(20−yardline,0)'],['quarter_seconds_remaining','Relógio no início da jogada','Contínua; indicador últimos 120s Q2/Q4'],['score_differential','Placar ataque−defesa no início','Contínua, déficit=max(−score,0), déficit × end_half'],['air_yards','Profundidade do alvo perpendicular à LOS','Somente sensibilidade: contínua, max(−air,0), max(air−20,0)']]
 coverage=table(['Ano','n','wind presente','temp presente','air_yards ausente'],[[y,v['target']['n'],f"{100*(1-v['nulls']['wind']/v['target']['n']):.2f}%",f"{100*(1-v['nulls']['temp']/v['target']['n']):.2f}%",v['nulls']['air_yards']] for y,v in a.items()])
 put('FEATURE-AVAILABILITY.md',f'''# Features e fronteira de informação

{table(['Campo','Significado','Tratamento fixo'],feature_rows)}

Principal: as seis colunas brutas anteriores ao passe estão completas em todos os 78.460 elegíveis. A implementação usa nove termos numéricos e duas categorias; fit 2022–24 produz 18 coeficientes + intercepto. Mediana/indicador de ausência e StandardScaler são ajustados exclusivamente no treino; categorias desconhecidas ficam com zeros no one-hot. A escolha de colunas é allowlist, não seleção baseada no teste. Features geradas conservam nulos antes da imputação. Não há time/QB/receiver/defesa como feature.

Air_yards é resultado da escolha e realização do lançamento, não informação pré-passe garantida. A variante não serve a uma previsão pré-snap equivalente. A profundidade em si não é decisão boa/ruim. Duas ausências históricas recebem mediana e indicadores aprendidos só no treino; zero ausências em 2024–26. Hinge e coluna ausente são colineares em duas raras linhas; regularização estabiliza o fit, mas coeficientes desses indicadores não têm interpretação substantiva.

{coverage}

**Ambientais excluídas de ambos os modelos antes do treino**: cobertura muda muito por temporada/estádio/roof; timestamp de medição anterior ao passe não demonstrado. Wind ausente permanece desconhecido, nunca vento zero. Roof é somente auditoria de grupo, não feature; mesmo quando conhecido, optamos por uma baseline situacional mais simples. [Cobertura por estádio](evidence/environment_by_stadium.csv) contém n e jogos, vento/temperatura presentes. [Distribuições](evidence/feature_distributions.csv) mostram nulos, médias, quantis e extremos por ano. Sem probabilidades inventadas de vento.

Campos de resultado (INT, EPA, reception/drop/catchability, texto, placar posterior), identidade e agregados futuros excluídos. Sem WP, odds, `read_thrown`, `qb_hit`, blitz, pass rushers, saída do pocket, participação ou tempo para lançar. `qb_hit==0` não é clean pocket. A [agenda oficial](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html) informa que participação FTN desde 2023 só é disponibilizada após a pós-temporada, não continuamente; não simulamos pressão2026 com outros campos.

Revisões históricas do PBP e features derivadas hoje não provam que os mesmos bytes estavam disponíveis em tempo real. A avaliação é retrospectiva. Metadados de campo pré-jogada vêm do [dicionário PBP oficial](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv), congelado no store. Ranges são validados; nenhum valor foi substituído com informação futura. Score pré-jogada foi conferido contra seus componentes.

Associação de coeficientes: descida4 tem maior log-odds que descida1 neste fit, mas categorias não têm referência única (one-hot completo penalizado), e transformações compartilham efeitos. Consulte coeficientes e parâmetros de escala, sem ler um coeficiente isolado como efeito causal. O modelo não observa defesa/cobertura, precisão, alternativas ou instruções da comissão.
''')
 metricrows=[]
 for label,v in [('Constante',m['context']['constant']),('Contexto principal',m['context']['model']),('+ profundidade',m['depth']['model'])]:metricrows.append([label,f"{v['log_loss']:.8f}",f"{v['brier']:.8f}",f"{v['pr_auc_average_precision']:.6f}",f"{v['roc_auc']:.6f}",f"{100*v['mean_probability']:.3f}%",f"{v['expected']:.2f}"])
 mt=table(['Modelo','Log loss ↓','Brier ↓','PR/AP ↑','ROC-AUC ↑','Prob. média','Soma esperada'],metricrows)
 val=table(['Validação','Treino','Const. LL','Contexto LL','Profundidade LL','Const. Brier','Contexto Brier','Profundidade Brier'],[[y,'2022' if y==2023 else '2022–23']+[f"{next(x for x in dev if x['variant']==variant and x['C']==.1 and x['validation']==y)[which][metric]:.8f}" for variant,which,metric in [('context','constant','log_loss'),('context','model','log_loss'),('depth','model','log_loss'),('context','constant','brier'),('context','model','brier'),('depth','model','brier')]] for y in [2023,2024]])
 cib=table(['Variante','Métrica','Delta modelo−constante','IC95% por jogos'],[[v,metric,f"{g['delta']:.8f}",f"[{g['low']:.8f}; {g['high']:.8f}]"] for v in m for metric,g in m[v]['paired_game_bootstrap'].items()])
 ct=table(['Faixa p','n','Positivos','p médio','Taxa observada'],[[r['bin'],r['n'],r['positives'],'—' if not r['n'] else f"{100*r['mean_probability']:.2f}%",'—' if not r['n'] else f"{100*r['observed_rate']:.2f}%"] for r in cal])
 put('MODEL-CARD.md',f'''# Model card — pesquisa v1, não produção

Estimador: regressão logística binária L2, C=0.1, solver lbfgs, tolerância1e-9, máximo2.000 iterações; sem class weights/oversampling. C selecionado entre [.01,.1,1,10] pela média por passe da log loss dos folds temporais 2023 e 2024. Configuração congelada no commit `35ac931`, SHA `3add5c6113c91f720ae7dfde759617f114daf66f700b4ce7229c2efa21f3e90a`. Sem ajuste com desempenho de 2025 ou ranking2026. [Contrato](RESEARCH-CONTRACT.md) e [freeze](evidence/frozen-config.json).

Treino final2022–24: 53.996 passes/2.270 positivos (4,204%); teste2025: 17.358/553 (3,186%). Baseline constante usa somente prevalência de treino. Variante com profundidade usa o mesmo alvo/população/protocolo, com pergunta condicional diferente. Sem pós-calibração.

{val}

Teste temporal2025 (sem refit após inspeção):

{mt}

{cib}

PR-AUC aqui é `sklearn.metrics.average_precision_score` (AP ponderada por incrementos de recall), não integração trapezoidal. Constante AP=prevalência de teste, ROC=.5. Accuracy não é argumento de utilidade. LL/Brier calculados em todos os passes com peso igual; intervalos pareados usam jogos inteiros sorteados com reposição, 2.000 réplicas, seed20261104. Intervalos condicionais aos modelos já treinados; não incluem incerteza da seleção ou verdade do alvo.

Calibração principal:

{ct}

Probabilidade média4,231% versus3,186% observada: **superestimação de cerca de181,5 rótulos em 2025**. Nas faixas com maior suporte, 3,49% estimado versus2,69% observado (n6.576) e 4,45% versus3,19% (n4.987). Não está adequadamente calibrado em nível para uso individual. A variante com profundidade também superestima (4,245% média), apesar de discriminar melhor. Brier melhor não resolve isso. Faixa superior da variante tem somente3 passes/1 positivo; não sustenta precisão. Gráfico e CSV preservam todas as faixas, inclusive vazias; barras Wilson são descritivas por passe, sem correção de cluster.

Grupos de teste em `groups_context/depth.json`, com critério descritivo n>=200 e positivos>=10. Contexto perde para constante na terceira descida (n4.497; LL0,16808 vs0,16669) e no quarto período (n4.891; LL0,15624 vs0,15608), embora melhore no total. OT (n101/3positivos) e roof `open` sem suporte suficiente não recebem inferência de estabilidade. Múltiplos grupos não constituem bateria confirmatória corrigida.

Aplicação: refit2022–25 com configuração congelada, 2026W1–7; 7.106 passes/219 positivos, esperado282,19 (3,971% vs3,082%). Uso permitido nesta entrega: exploração condicionada e diagnóstico do modelo. Sem ranking definitivo de habilidade, culpa, decisão ou previsão individual confiável; sem avaliação causal, persistência de talento ou sorte nas INT.

Serialização: JSON transparente com features, medianas, indicadores, médias/escalas, categorias, coeficientes e intercepto, versão `qb-iw-json-logistic-v1`. Sem pickle/joblib e sem carregar modelo externo. Preditor JSON é confrontado com sklearn no treino e aplicação (atol1e-13/rtol1e-12); modelos/hash no freeze. Implementação/schema e versões devem acompanhar o JSON; não é formato universal garantido entre versões. Não carregar JSON arbitrário como artefato confiável de produção.

Limitações: mudança de prevalência/definição do provedor não explicada; período curto; charting subjetivo; dados revisados retrospectivamente; modelos de contexto incompletos; dependência entre passes; identidade de posição não certificada; bootstrap não inclui toda incerteza. [Atribuição/licença](NOTICE.md). Próximo experimento deve tratar deriva e calibração em novo bloco temporal, antes de dar significado comparativo aos resíduos.
''')
 grouprows=[[g['group'],g['value'],g['n'],g['positives'],f"{g['log_loss']-g['constant_log_loss']:+.6f}"] for g in groups if g['support_sufficient']]
 qrows=[]
 for r in q.sort_values(['names','passer_player_id']).itertuples():
  ci='sem IC (<3 jogos)' if pd.isna(r.ci_low_per100) else f'[{r.ci_low_per100:+.2f}; {r.ci_high_per100:+.2f}]'+(' †' if r.observed==0 else '')
  qrows.append([r.passer_player_id,r.names,r.teams,r.passes,r.games,r.observed,f'{r.expected:.2f}',f'{100*r.observed_rate:.2f}%',f'{100*r.expected_rate:.2f}%',f'{r.difference_count:+.2f}',f'{r.difference_per100:+.2f}',ci,r.interceptions])
 qt=table(['GSIS ID','Nome','Equipes','n','Jogos','FTN obs.','Esp.','Taxa obs.','Taxa esp.','O−E','Por100','IC95% jogos','INT'],qrows)
 put('REPORT.md',f'''# Passes interceptáveis acima do esperado — primeira entrega

**Conclusão:** a base permite pesquisa retrospectiva reconciliada. O contexto pré-jogada melhora modestamente a log loss fora do treino, mas **as probabilidades superestimam o nível do alvo e não sustentam ranking de qualidade/decisão de QBs**. Entrega concluída como baseline executada, avaliada e reproduzível; não pronta para produção. A variante com air_yards discrimina melhor e responde a outra pergunta, sem resolver o desvio de calibração.

## O que foi observado

{counts}

Zero duplicatas, rótulos elegíveis ausentes ou passers ausentes; reconciliação independente exata em fontes brutas. As pistas anteriores coincidiram sem forçar totais. População mantém throwaways/incompletos, penalidades com tentativa válida, receiver desconhecido e overtime; exclui sacks/scrambles, spikes, anuladas/no_play, conversões e postseason. Dados do site e snapshots não alterados. [Funil/joins/casos especiais](DATA-AUDIT.md).

A frequência cai de5,23% em2022 para3,19% em2025. O mecanismo da queda é desconhecido. Charting é avaliação FTN, não medida incontestável do comportamento do QB. Todos os QBs estão representados no conjunto maior de62 passers identificados, que também inclui lançadores ocasionais; posição de roster não certificada.

## O que foi estimado fora do período de treino

Dois folds expansivos exclusivos de desenvolvimento, sem sorteio de jogadas:

{val}

Busca pequena predefinida selecionou C=.1 em ambas. Freeze e modelos2022–24 foram commitados antes da avaliação2025. Teste final único, sem recalibrar/reselecionar para consertá-lo:

{mt}

{cib}

O ganho principal de LL é aproximadamente0,94% relativo à constante; o ganho de Brier é pequeno e seu intervalo inclui zero. Isso é evidência limitada de informação contextual, não um grande avanço nem boa calibração. Profundidade reduz LL em cerca de5,73% relativo à constante, mas condicionar uma escolha do QB retira da pergunta parte do que queremos examinar. Não a promovemos a principal por produzir métricas ou ordenação mais atraentes.

## Calibração e estabilidade

![Calibração2025](figures/calibration_2025.png)

{ct}

734,47 esperados contra553 observados; constante729,73. O contexto não corrige a queda temporal de prevalência. As faixas de suporte alto superestimam consistentemente; não chamamos as probabilidades de razoavelmente calibradas no teste. A faixa profunda de p>=25% tem n3 e incerteza enorme, mostrada separadamente no gráfico para preservar a leitura das faixas maiores. [Faixas das duas variantes](evidence/calibration_context.json), [sensibilidade](evidence/calibration_depth.json).

{table(['Grupo','Faixa','n','Positivos','Delta LL contexto−constante'],grouprows)}

Há ganhos e perdas por grupo; terceira descida eQ4 pioram. Suporte mínimo é convenção de diagnóstico, não garantia. Sem inferência para OT de101 passes/3positivos ou roof open de baixo suporte. Diferenças de distância/score/relógio e cobertura ambiental estão nas [distribuições por ano](evidence/feature_distributions.csv). Não identificamos causa do drift somente com esses agregados; não adicionamos vento nem deslocamento de intercepto usando o teste.

## Aplicação exploratória2026 W1–7

Refit2022–25, configuração já congelada. **7.106 passes/107jogos/219 rótulos**, esperado contextual282,19. Taxa estimada3,971%, observada3,082%; diferença total−63,19 (−0,889 por100). O deslocamento global faz muitos resíduos negativos: não significa que a maioria dos jogadores tenha habilidade superior a uma referência calibrada.

![Observado versus esperado](figures/observed_expected_2026.png)

![Diferença por100](figures/difference_per100_2026.png)

Gráfico alfabético com32 passers de100+tentativas por legibilidade; corte exploratório, não garantia estatística. Tabela abaixo inclui os62 identificadores e todos os volumes. Não se força ordem precisa. Intervalos percentis95% reamostram jogos de cada passer (2.000, seed20261104), modelo fixo; com<3jogos não emitimos IC. `†`: zero positivos torna o bootstrap empírico especialmente degenerado — só reamostra os zeros já vistos, não limita a verdadeira taxa latente. Mesmo os demais ICs ignoram incerteza de treino, seleção, charting e mudança de população; não são intervalos de habilidade persistente nem testes simultâneos de62 jogadores. Jogos nos quais o jogador não lançou não entram no suporte.

{qt}

[CSV contextual](evidence/qb_context.csv) preserva precisão total e [CSV com profundidade](evidence/qb_depth.csv) usa os mesmos IDs. Taxas de tabela estão em porcentagem; CSV guarda frações. `INT` é desfecho observado separado, sem modelo de sorte. Positivo em Por100 = mais rótulos FTN que esta baseline contextual esperava, não pior QB.

## Dependência da profundidade escolhida

![Sensibilidade](figures/depth_sensitivity_2026.png)

A variante espera283,69 rótulos no total, também acima de219. Entre os32 com100+passes, a mudança do residual fica entre−0,495 e+0,458 por100. Três sinais mudam perto de zero: J.Allen +0,336→−0,040, T.Huntley −0,024→+0,433, B.Nix −0,263→+0,123. Não tratamos essas trocas como descobertas sobre personalidade ou decisão. [Comparação completa](evidence/qb_sensitivity.csv). Sem escolha de variante a partir de uma lista de nomes; nenhuma tese prévia sobre Herbert/Geno/Darnold foi testada como hipótese a confirmar.

## O que permanece desconhecido

Não conhecemos estabilidade do protocolo FTN entre anos, concordância entre anotadores, completude de todas as jogadas possíveis, disponibilidade histórica exata dos bytes, qualidade da cobertura defensiva/alternativas, instruções de jogada e quem deveria receber responsabilidade. Rótulo positivo e INT discordam legitimamente como variáveis diferentes. O residual mistura contexto não observado, escolha do passe, execução, charting, acaso amostral e possível efeito do QB. Associação não é causalidade. O histórico4anos e a janela7semanas não mostram persistência de habilidade. [Model card](MODEL-CARD.md), [features](FEATURE-AVAILABILITY.md), [licença](NOTICE.md).

## Falhas e correções preservadas

1. 404 ao buscar LICENSE sem extensão: corrigido para LICENSE.md; retomada verifica hashes, sem rebaixar falha silenciosamente.
2. build-v1 abortou por colisão de colunas de agregação no comparador independente; corrigida para sum_y/sum_i; build-v2 refeito em destino novo. Nenhum total foi ajustado.
3. Cinco falhas iniciais de fixture por colocar alvo nos dois lados do join; fixture passou a refletir PBP/FTN separados, sem mudar expectativa de cardinalidade/ausência.
4. NumPy2.2.6/Accelerate produziu avisos espúrios até em ones@zeros; single-thread não resolveu. Somente venv isolado atualizado para2.3.4; desenvolvimento refeito com RuntimeWarning como erro. Conferência inicial de equivalência entre versões com tolerância1e-10 falhou para coeficientes de profundidade (máximo3,97e-9). A avaliação já usou o modelo novo congelado; não houve retuning. Diagnóstico posterior quantificou diferença máxima em probabilidades de treino de1,81e-9, multiplicação independente difere3,55e-15 e não há avisos no ambiente final. Essa diferença entre versões não é alegada como identidade byte a byte; reprodução usa o mesmo lock e deve conferir hashes. [Prova numérica](evidence/numerical-check.json).
5. Figura inicial recortava a faixa de baixo suporte da variante; corrigida com painel separado, preservando todos os suportes e sem mudar métricas. FutureWarning do matplotlib com Series de 1 elemento corrigido convertendo arrays; nenhum aviso foi silenciado globalmente.

Tentativas, logs e saídas intermediárias foram mantidos no store. Contrato/features/protocolo não foram modificados após o teste para melhorar resultado. [Checkpoints](CHECKPOINTS.md) e [reprodução](README.md).

## Decisão e próximo experimento justificável

Manter esta baseline como referência de pesquisa. Antes de exibir resíduos como comparação de QBs, investigar a queda de prevalência e estabilidade do charting. Pré-registrar **um experimento de adaptação/calibração temporal** (p.ex. janela recente e correção de intercepto aprendida somente em previsões temporais anteriores), com o mesmo alvo/contexto e um novo bloco temporal reservado.2025 agora é dado examinado; não reutilizá-lo como teste virgem. Não corrigir níveis diretamente com a taxa2026 para depois apresentar os mesmos QBs como avaliação independente. Em paralelo documental, validar posições por roster e obter definição operacional de anotação; sem construir outro modelo de INT/pressão, sem ampliar algoritmos ou interface. Reservar semanas ainda não examinadas ou temporada posterior e definir critério de calibração/ganho antes de abrir resultados.
''')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--store',required=True);p.add_argument('--docs',required=True);x=p.parse_args();write_docs(x.store,x.docs)
