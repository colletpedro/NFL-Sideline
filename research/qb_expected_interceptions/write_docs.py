"""Materialize the Portuguese report directly from pinned research results."""
import shutil
import pandas as pd
from common import *

def table(headers,rows):
    return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(str(x).replace('|','/') for x in r)+' |' for r in rows])

def fmt(x,d=4):return f'{x:.{d}f}'

def generate(store=STORE):
    store=Path(store);app=store/'application-complete';m=pd.read_csv(store/'evaluation/metrics.csv');am=pd.read_csv(app/'metrics.csv');q=pd.read_csv(app/'players.csv')
    development=pd.read_csv(store/'development/development/metrics.csv');selection=read(store/'development/selection.json');bs=read(store/'evaluation/paired_bootstrap.json');cases=read(app/'cases.json')['cases']
    audit=read(store/'build/audit/raw.json');cross=pd.read_csv(store/'build/audit/cross_by_season.csv');coverage=read(store/'build/coverage.json');sources=read(store/'sources.json');model=read(store/'final/model.json')
    p1=model['groups']['1']['probability'];p0=model['groups']['0']['probability']
    def metrics_table(data,group):
        a=data[data.group.eq(group)]
        return table(['Procedimento','Log loss','Brier','Average precision','ROC-AUC','Prev. %','Média prevista %','Obs.','Esp.','O/E'],
            [[r.model,fmt(r.log_loss,6),fmt(r.brier,6),fmt(r.average_precision,6),fmt(r.roc_auc,6),fmt(100*r.prevalence,3),fmt(100*r.mean_prediction,3),r.observed_interceptions,fmt(r.expected_interceptions,3),fmt(r.observed_expected_ratio,3)] for r in a.itertuples()])
    report=f'''# Interceptações sofridas em relação ao risco dos passes — relatório v1

**Entrega concluída para revisão, 05/11/2026. Escolhido B2, referência recente condicionada à classificação FTN.** A regressão contextual não mostrou ganho defensável. A avaliação temporal de 2025 tem calibração global próxima, mas subestima INT nos passes FTN=0. A aplicação exploratória atual contém 121 jogos de 2026, W1–8, e não altera o laboratório aprovado.

Pergunta respondida: comparar interceptações observadas com uma referência estatística condicionada à classificação retrospectiva de cada passe. O alvo é INT efetiva do PBP. O M3 continua estimando **passes interceptáveis**, com seus parâmetros e previsões preservados. Não transformamos a expectativa do M3 em INT esperadas.

## Escolha antes da avaliação de 2025

O [contrato](RESEARCH-CONTRACT.md) foi versionado em `4c705fb`, antes das novas comparações. O desenvolvimento e os modelos para 2025 foram congelados em `decbc33`, antes da execução da avaliação. Os períodos já tinham contagens examinadas: isto é avaliação retrospectiva temporal fora do ajuste, sem alegar confirmação intocada.

Treinos/avaliações: 2022→2023; 2022–2023→2024; fit 2022–2024→2025. B2 usa apenas a temporada completa imediatamente anterior em cada fold. Jogos inteiros, sem sortear passes. Medianas/escalas/categorias são ajustadas somente no treino. C usa exclusivamente FTN, descida, distância, campo, quarto, relógio e diferença de placar pré-jogada, com as transformações fixas auditadas da pesquisa anterior.

Busca fechada de C: `.01, .1, 1`; escolhido **.1** pela log loss agrupada por passe em 2023/2024. A regra exigia ganho pareado de C sobre B1 **e** B2, Brier sem piora material e O/E entre .8 e 1.25 em cada grupo FTN. C falhou; B2 venceu a comparação predefinida entre referências. Nenhuma alteração estatística após abrir 2025.

{metrics_table(development,'all')}

Em desenvolvimento, C−B2 teve delta de log loss {selection['paired']['C-B2']['log_loss']['delta']:+.6f}, IC descritivo de bootstrap [{selection['paired']['C-B2']['log_loss']['low']:+.6f}, {selection['paired']['C-B2']['log_loss']['high']:+.6f}]. O sinal favorece B2. C também falhou na calibração por grupo. [Seleção completa](evidence/selection.json), [métricas por grupo](evidence/development-metrics.csv), [freeze original](evidence/freeze.json).

## Avaliação fora do ajuste em 2025

17.358 passes elegíveis, 272 jogos, 380 INT. B0 é a taxa global de treino; B1 são duas taxas históricas por FTN; B2 são duas taxas de 2024; C é a regressão com configuração congelada. As taxas com suporte interior são empíricas. Bordas zero/todos usam Jeffreys; grupo ausente recorre ao global e é marcado. Esses fallbacks não foram necessários nos grupos reais.

{metrics_table(m,'all')}

Average precision usa `sklearn.metrics.average_precision_score`, com incremento de recall; não é área trapezoidal. ROC-AUC é complementar. B1 e B2 têm as mesmas duas classes ordenadas e por isso empatam em AP/ROC-AUC, apesar de probabilidades/calibração diferentes. O grande ganho sobre B0 depende do rótulo FTN retrospectivo, que pode conhecer o desfecho; não prova previsão independente anterior ao evento.

### FTN=1: 553 passes, 305 INT

{metrics_table(m,'ftn_1')}

### FTN=0: 16.805 passes, 75 INT

{metrics_table(m,'ftn_0')}

Um total próximo esconde erro: B2 prevê 364,51 INT para 380 (O/E 1,043). Em FTN=1 prevê 311,59 para 305 (O/E 0,979). Em FTN=0 prevê **52,92 para 75** (O/E **1,417**; taxa prevista 0,3149%, observada 0,4463%). Portanto, não declaramos calibração uniforme ou prontidão para produção. Não recalibramos com os rótulos de 2025 para reavaliar o mesmo período.

### Diferenças pareadas de desempenho

Delta = primeiro procedimento menos segundo; negativo favorece o primeiro. Bootstrap de **jogos**, 2.000 réplicas, seed **20261105**, percentis 2,5/97,5, probabilidades pareadas fixas. Não é bootstrap de passes e não estima incerteza de habilidade por jogador.

'''
    report+=table(['Comparação','Delta log loss','95%','Delta Brier','95%'],[[k,fmt(v['log_loss']['delta'],6),f"[{v['log_loss']['low']:+.6f}, {v['log_loss']['high']:+.6f}]",fmt(v['brier']['delta'],6),f"[{v['brier']['low']:+.6f}, {v['brier']['high']:+.6f}]"] for k,v in bs['all'].items()])
    report+='''

C não supera B1 de forma convincente em log loss e é pior que B2 nos dois escores. A vantagem B2−B1 em log loss é pequena, com limite superior próximo de zero; o intervalo Brier cruza zero. Não usar esses intervalos como garantia de vantagem futura. Dependência entre jogos, incerteza dos parâmetros/charting e seleção de C não estão cobertas; sem correção de multiplicidade. [Comparações globais e por FTN](evidence/evaluation-bootstrap.json).

![Calibração](figures/calibration_global_and_ftn.png)

Bins fixos, com suporte/eventos completos em [CSV](figures/calibration_support.csv); bins vazios não são descartados da evidência. B2 tem duas probabilidades e produz somente dois pontos globais/um por grupo. Isso não é uma curva rica de risco dentro de cada grupo. Suporte n≥200 e eventos≥10 é marca descritiva, não certificação.

![Desempenho](figures/performance_vs_references_2025.png)

## Aplicação exploratória atual

'''
    report+=f'''Fontes públicas próprias adquiridas até `{sources['acquisitionCompletedAt']}`. Último jogo encerrado disponível: **{coverage['completed_through']}**. **{coverage['included_games']} de {coverage['completed_games']} jogos encerrados utilizáveis**, zero lacunas entre eles; 151 jogos ainda sem placar final no calendário. A disponibilidade é do arquivo adquirido, não uma afirmação de que toda a temporada já aconteceu. Aplicação aceita jogos válidos de semanas parciais; não requer fechamento semanal. [Cobertura e todos os jogos](evidence/coverage.json).

**7.970 passes; 242 FTN=1; 170 INT; 66 lançadores, 57 QBs e nove de outras posições (P/WR), estes com um passe cada.** Todas as posições e volumes permanecem na base e na [tabela completa](evidence/players-2026.csv). Identificação GSIS por roster semanal/temporada/equipe; não por nome abreviado. Nenhuma posição desconhecida/conflitante nesta aquisição.

B2 final segue o procedimento escolhido e usa somente **2025**, a temporada completa anterior à aplicação: P(INT|FTN=1) = **{p1:.12f}** (305/553); P(INT|FTN=0) = **{p0:.12f}** (75/16.805). O refit do procedimento sobre o período disponível 2022–2025 tem essa janela recente por definição, não o pool de quatro temporadas. Modelo fixo `{model['model_id']}`, SHA-256 `{sha(store/'final/model.json')}`.

{metrics_table(am,'all')}

'''
    report+=table(['Grupo 2026','Passes','INT observadas','INT esperadas','O/E','Taxa observada %','Taxa prevista %'],[[r.group,r.n,r.observed_interceptions,fmt(r.expected_interceptions,4),fmt(r.observed_expected_ratio,4),fmt(100*r.prevalence,4),fmt(100*r.mean_prediction,4)] for r in am.itertuples()])
    report+='''

São 133,471971 esperadas em FTN=1 + 34,489735 em FTN=0 = **167,961706**. O/E global 1,012; FTN=1 1,049; FTN=0 0,870. A calibração atual parece próxima nos agregados, mas não elimina o erro retrospectivo de 2025 nem valida causalidade. Nenhum ajuste usa os rótulos de 2026.

![QBs](figures/qb_observed_vs_expected_2026.png)

X é INT esperadas; Y é INT sofridas. A linha é a identidade matemática observado=esperado, sem regressão ajustada aos jogadores. Acima significa mais INT que a estimativa; abaixo, menos. O painel principal tem 33 QBs com ≥100 passes; o [painel complementar](figures/small_support_all_positions_2026.png) mostra os outros 33 lançadores sem ocultar amostras pequenas. O corte serve apenas à legibilidade; todas as observações entram nos cálculos. Contagens neste gráfico; taxas separadas na tabela.

![Decomposição](figures/expected_decomposition_2026.png)

## Exemplos determinados pelo contrato

Critérios predefinidos: QB com ≥100 passes mais próximo da igualdade, maior residual positivo, menor residual negativo, menor suporte entre todos os lançadores, e QB com mais INT em FTN=0; empates por GSIS. São exemplos selecionados, não amostra aleatória nem validação de vídeo. Nenhum intervalo individual foi calculado.

'''
    report+=table(['Caso','Jogador / GSIS','Passes / jogos','FTN=1','INT','Esp. FTN=1 + FTN=0','Esp. total','Obs−Esp','Por 100'],[[r['case'],r['name']+' / '+r['gsis_id'],f"{r['eligible_passes']} / {r['games']}",r['ftn_interception_worthy_passes'],r['observed_interceptions'],f"{r['expected_from_ftn_1']:.4f} + {r['expected_from_ftn_0']:.4f}",fmt(r['expected_interceptions']),fmt(r['observed_minus_expected']),fmt(r['difference_per_100_passes'])] for r in cases])
    interpretation={
        'near_identity':'Cousins fica próximo da referência agregada. Essa proximidade não mede habilidade, responsabilidade ou precisão do modelo por passe.',
        'above_identity':'Darnold está acima da estimativa. Seu total inclui duas INT no grupo FTN=0. O residual positivo não permite atribuir as causas ao jogador ou a uma suposta sorte.',
        'below_identity':'Love está abaixo da estimativa, mas 13 classificações FTN=1 não significam que deveriam existir 13 INT. Não inferimos interceptações derrubadas pela diferença entre essas contagens.',
        'low_support':'Dalton tem somente uma tentativa e uma INT. A taxa por 100 é uma reexpressão aritmética extremamente instável; não é projeção de 100 passes nem evidência de habilidade. Não há intervalo degenerado de zero eventos ou ranking causal.',
        'interception_in_ftn_0':'Rodgers tem cinco das seis INT em FTN=0. A expectativa inclui os dois grupos; não inferimos responsabilidade do recebedor, defensor ou QB pela descrição/nome.'}
    for r in cases:
        tag=r['case'];plays=pd.read_csv(app/f'cases/{tag}_all_plays.csv');ints=plays[plays.interception.eq(1)]
        n1=r['ftn_interception_worthy_passes'];n0=r['eligible_passes']-n1
        report+=f'''

### {r['name']} — {tag}

{r['teams']}; {r['period_start']} a {r['period_end']}. Composição: {n1} × {p1:.8f} + {n0} × {p0:.8f} = {r['expected_interceptions']:.6f} INT esperadas. Observadas: {r['observed_interceptions']}, sendo {r['observed_in_ftn_1']} em FTN=1 e {r['observed_in_ftn_0']} em FTN=0. {interpretation[tag]}

[Todas as {r['eligible_passes']} jogadas que sustentam o esperado](evidence/cases/{tag}_all_plays.csv) · [FTN=1 e/ou INT, com descrições originais](evidence/cases/{tag}_events_and_ftn.csv). As linhas sem evento também contribuem para o esperado. Não reconstituímos culpa pelas descrições.

'''
        report+=table(['Jogo','Play ID','FTN=1','INT','P(INT)'],[[x.game_id,int(x.play_id),int(x.is_interception_worthy),int(x.interception),fmt(x.p_interception_given_ftn,8)] for x in ints.itertuples()])
    dj=q[q.name.eq('Daniel Jones')].iloc[0]
    report+=f'''

Daniel Jones também ilustra a distinção da pergunta original: {dj.eligible_passes} passes, {dj.ftn_interception_worthy_passes} FTN=1, {dj.observed_interceptions} INT, **{dj.expected_interceptions:.4f} INT esperadas** ({dj.expected_from_ftn_1:.4f} + {dj.expected_from_ftn_0:.4f}). O M3 do laboratório trata de outra variável; 17 classificações FTN não implicam 17 INT nem uma contagem de INT derrubadas.

## Integridade, reprodução e limites

Auditoria independente dos quatro cruzamentos em SQL, por temporada/semana/jogo, sem redefinir população. Histórico pinado 2022–2025 confere exatamente nas chaves, GSIS, FTN, INT e contexto autorizado. Novas fontes 2026 têm hashes diferentes das fontes do laboratório, mas o overlap elegível de 7.970 passes não mudou nos campos auditados. Sem duplicatas, alvo/FTN/GSIS ausentes no universo incluído. [Auditoria completa](DATA-AUDIT.md).

**FTN pode conhecer o desfecho. Não há evidência de anotação cega ao resultado.** Esta limitação acompanha contrato, model card e pacote de consumo. O desempenho usando FTN não demonstra previsão independente anterior à INT. Residual não mede automaticamente sorte, culpa, decisão ou qualidade do QB. Ausência de tracking/film/alternativas e de identificação causal impede resolver responsabilidade individual.

2025/2026 já eram conhecidos; previsões fora do ajuste não convertem a avaliação em confirmação intocada. Fontes podem ser corrigidas; join completo não certifica verdade ou completude do charting. B2 não distingue contexto dentro de cada grupo e transporta a taxa de uma temporada; a subestimação em FTN=0 em 2025 é um limite material. Sem calibração pós-hoc, intervalos de habilidade ou promoção a produção.

**33 testes novos + 59 preservados passaram**, em processos separados devido a módulos legados homônimos. Reprodução offline em destino novo: **156 arquivos científicos idênticos em bytes**, incluindo modelos, previsões, agregados e PNG/SVG. Equivalência numérica adicional para CSV/Parquet: atol 1e-12, rtol 1e-10. Igualdade local de bytes não é garantia entre plataformas/BLAS/renderers. Inventários de ambiente são excluídos da identidade científica. [Recibo](evidence/reproduction.json).

Uma falha de I/O ao salvar os exemplos revelou `cases/` ausente. Corrigida somente a criação do diretório, com exceção de hash exata e registrada em [output-fix](evidence/output-fix.json). Freeze original e avaliação de 2025 permanecem intactos. A reprodução refez a seleção e todos os parâmetros: somente o hash do arquivo orquestrador difere no novo freeze; nenhuma configuração/feature/métrica foi corrigida após o teste. A execução parcial e as figuras iniciais continuam preservadas no store.

Pacote completo fora do Git em `{store}`; [manifest versionado](evidence/package-manifest.json), [contrato de consumo](../../../research/qb_expected_interceptions/consumer-contract.json), [índice revisável](evidence/consumer-index.json). Nenhum ponteiro ativo foi criado no laboratório. [Execução/atualização/reprodução](README.md) e [proposta posterior de integração](HANDOFF.md). Nenhum merge, push, deploy ou publicação externa.
'''
    (DOC/'REPORT.md').write_text(report)
    rows=[]
    for year,g in cross.groupby('season'):
        n=int(g.denominator.iloc[0]);cells={(int(x.iw),int(x.target)):int(x.n) for x in g.itertuples()}
        rows.append([year,n,*[cells[k] for k in [(1,1),(1,0),(0,1),(0,0)]],int(g[g.iw.eq(1)].group_denominator.iloc[0]),int(g[g.iw.eq(0)].group_denominator.iloc[0])])
    audit_text=f'''# Auditoria de dados e do alvo — XINT v1

Aquisição própria: `{sources['acquisitionCompletedAt']}`. [Manifest completo com URLs, instantes, tamanhos, SHA-256, atribuição e licenças](evidence/sources.json). Histórico 2022–2025 copiado após conferir todos os hashes do manifest v1; sem nova aquisição que substitua essas revisões. Os manifests antigos, dados e pesquisas permanecem intactos. Modelo não lê `.env`, banco ou ETL operacional.

## População e quatro cruzamentos

Mesma definição aprovada: REG; play_deleted=0; play_type=pass; pass_attempt=1; sack=0; qb_scramble=0; qb_spike=0; two_point_attempt=0; GSIS e FTN explícitos. Overtime incluído; penalidades permanecem somente se PBP conserva a tentativa válida. Nulo não vira zero, FTN ausente não vira False. Sem filtro de posição para construir o modelo.

{table(['Temporada','Passes','FTN=1 / INT=1','FTN=1 / INT=0','FTN=0 / INT=1','FTN=0 / INT=0','Den. FTN=1','Den. FTN=0'],rows)}

Os quatro cruzamentos somam exatamente o denominador em cada unidade. [Por semana](evidence/cross-by-week.csv) e [por jogo](evidence/cross-by-game.csv) repetem todas as quatro células, inclusive zeros, denominador total e denominador do grupo FTN. A segunda rotina parte dos arquivos brutos, aplica WHERE/LEFT JOIN em SQLite e compara chaves, GSIS, FTN e INT com pandas antes de confrontar todas as células/denominadores. [Recibos](evidence/independent-reconciliation.json). Não usa o agregado do modelo como fonte de verdade.

## Semântica do alvo

O [dicionário PBP oficial pinado](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_pbp.csv) define interception como indicador binário de passe interceptado; pass_attempt também inclui sacks, que o filtro remove. score_differential se refere ao início da jogada, conferido contra posteam_score−defteam_score. Placar posterior, EPA, texto e identificadores não são features. O alvo é um desfecho registrado, não um rótulo de culpa.

[Consistência independente dos campos de evento](evidence/target-consistency.json): zero INT sem GSIS de interceptador, zero GSIS de interceptador em passe com INT=0, zero INT simultaneamente marcadas complete_pass ou incomplete_pass nos elegíveis; zero INT em no_play nas fontes adquiridas. Isso é verificação mecânica do alvo, sem inferir responsabilidade a partir de nomes. Descrições completas ficam nos Parquets/JSONs e nos casos para inspeção posterior.

{table(['Ano','Penalidades elegíveis / INT','Overtime elegível / INT','FTN=1 em no_play excluído','INT em dois pontos excluídos','Alvo/GSIS ausente incluído'],[[r['season'],f"{r['eligible_penalty']} / {r['eligible_penalty_int']}",f"{r['eligible_overtime']} / {r['eligible_overtime_int']}",r['excluded_no_play_worthy'],r['excluded_two_point_int'],f"{r['target_missing_included']} / {r['gsis_missing_included']}"] for r in audit])}

Jogadas anuladas, deletadas e dois pontos ficam fora conforme flags/classificação, sem reclassificação por texto. `audit/excluded_YYYY.parquet` conserva linhas/descritivos excluídos. [Funil, nulls de flags e contagens brutas](evidence/raw-audit.json). Todas as chaves PBP e FTN são únicas/não nulas; duplicata até idêntica aborta. Sem deduplicação arbitrária. FTN sem chave PBP: zero nas fontes adquiridas. Todas as tentativas incluídas encontraram um rótulo binário e alvo binário.

## Cobertura e revisão

Histórico elegível: 271 jogos em 2022; 272 em cada ano 2023–2025. Exatamente a base histórica reconciliada anterior; a ausência do jogo cancelado de 2022 não é preenchida. Nenhuma janela foi redefinida para melhorar os números. 2026: {coverage['included_games']} jogos encerrados e utilizáveis, W1–8, até {coverage['completed_through']}; zero pendências entre encerrados e 151 ainda sem resultado final. Cada um consta no [arquivo de cobertura](evidence/coverage.json).

O gate por jogo exige trio de placar consistente, marcador END GAME único com placar final concordante, calendário/semana/equipes/data concordantes, charting e identidade completos. END GAME é apenas gate de encerramento; descrição não entra no modelo. Um jogo sem alvo/FTN/GSIS/contexto fica como lacuna e outros jogos válidos entram, mesmo em semana parcial. Testes simulam todas essas lacunas. Contradições estruturais abortam em vez de escolher uma revisão.

PBP e FTN 2026 novos têm hashes diferentes do pacote aprovado; **zero adições, remoções ou alterações** nas chaves e campos elegíveis auditados em 7.970 passes: FTN, INT, GSIS e contexto. Não afirmar que todo byte ou campo bruto permaneceu igual. [Revisão](evidence/revision.json). Histórico 2022–2025 pinado não foi redownloaded; sua revisão é a já reconciliada da pesquisa v1, não informação conhecida em tempo real naquele ano. Não temos o histórico completo de revisões do provedor.

## Identificação

GSIS é a identidade; roster semanal por temporada+semana+equipe fornece nome completo e posição. Aliases documentados LAR→LA, JAC→JAX, WSH→WAS. Conflito ou ausência permanece unknown_or_conflicting, nunca resolvido por nome. Troca de equipe não cria outro jogador. Nome PBP é conservado ao lado do nome auditado; se roster não resolve nome, apenas exibição usa fallback PBP.

Em 2026, 66 lançadores: 57 QB, nove P/WR, nenhum desconhecido/conflitante; 7.961 tentativas QB e nove outras. [Identidade por equipe/temporada](evidence/identity.csv). As posições não são features nem filtro estatístico; tabelas e figuras identificam os ocasionais separadamente.

## Rótulo FTN e licenças

[FTN loader oficial](https://nflreadr.nflverse.com/reference/load_ftn_charting.html) descreve charting manual disponível desde 2022; [dicionário](https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html) identifica is_interception_worthy. **A anotação/revisão pode conhecer o desfecho; não temos evidência de revisão cega.** `date_pulled` representa obtenção pela rotina do provedor, não comprova instante de anotação nem cegueira. Não usar bom desempenho condicionado ao rótulo como prova de previsão anterior à INT.

FTN: **FTN Data via nflverse, CC BY-SA 4.0**, dados transformados, sem endosso. PBP/roster/schedule: atribuição/licença geral nflverse-data CC BY 4.0, com escopo subjacente não certificado juridicamente. [Licença pinada](https://raw.githubusercontent.com/nflverse/nflverse-data/main/LICENSE.md), bytes no store/documentation. Preservar atribuição e tratar obrigações aplicáveis dos derivados numa futura publicação. Esta entrega não publica dados/modelo/site externamente.
'''
    (DOC/'DATA-AUDIT.md').write_text(audit_text)

if __name__=='__main__':generate()
