"""Compose review documents from frozen retrospective artifacts only."""
from pathlib import Path
import argparse,json
import pandas as pd

def table(headers,rows):return '| '+' | '.join(headers)+' |\n| '+' | '.join(['---']*len(headers))+' |\n'+''.join('| '+' | '.join(map(str,r))+' |\n' for r in rows)
def run(store,docs):
 s=Path(store);doc=Path(docs);e=s/'experiment-verified';metrics=json.loads((e/'metrics.json').read_text());selection=json.loads((e/'selection.json').read_text());std=pd.read_csv(e/'drift/standardization.csv');comp=pd.read_csv(e/'drift/composition.csv');positions=pd.read_csv(e/'passer_presentation.csv');status=json.loads((s/'reserved-status.json').read_text());freeze=json.loads((e/'frozen/freeze.json').read_text())
 def put(name,text):(doc/name).write_text(text.strip()+'\n')
 def m(year,name):return next(r for r in metrics if r['year']==year and r['candidate']==name)
 metric_table=table(['Período conhecido','Modelo','LL ↓','Brier ↓','AP ↑','AUC ↑','Observados','Esperados','O/E'],[[str(r['year'])+(' W1–7' if r['year']==2026 else ''),r['candidate'],f"{r['model']['log_loss']:.8f}",f"{r['model']['brier']:.8f}",f"{r['model']['pr_auc_average_precision']:.6f}",f"{r['model']['roc_auc']:.6f}",r['model']['positives'],f"{r['model']['expected']:.2f}",f"{r['model']['observed_expected']:.3f}"] for r in metrics])
 diff_table=table(['Ano','M3−M1 LL','IC95% jogos','M3−M1 Brier','IC95% jogos'],[[year,f"{m(year,'M3')['difference_vs_M1']['log_loss']['delta']:.8f}",f"[{m(year,'M3')['difference_vs_M1']['log_loss']['low']:.8f}; {m(year,'M3')['difference_vs_M1']['log_loss']['high']:.8f}]",f"{m(year,'M3')['difference_vs_M1']['brier']['delta']:.8f}",f"[{m(year,'M3')['difference_vs_M1']['brier']['low']:.8f}; {m(year,'M3')['difference_vs_M1']['brier']['high']:.8f}]"] for year in [2024,2025,2026]])
 st=table(['Células','Ano','n comum / total','Taxa crua no suporte','Taxa padronizada','Peso máx.','ESS'],[[r.spec,r.season,f'{r.n_common}/{r.n_full}',f'{100*r.prevalence_common:.3f}%',f'{100*r.standardized:.3f}%',f'{r.max_weight:.3f}',f'{r.effective_sample_size:.1f}'] for r in std.itertuples()])
 ct=table(['Ano','Profundidade','n','FTN positivos','% dos passes','Taxa do rótulo'],[[r.season,r.level,r.n,r.y,f'{100*r.fraction:.2f}%',f'{100*r.prevalence:.2f}%'] for r in comp[(comp.group=='depth')&comp.season.isin([2022,2025,2026])&comp.level.ne('unknown')].itertuples()])
 put('DRIFT-AUDIT.md',f'''# Diagnóstico de queda temporal — composição não explica a maior parte

População v1 preservada integralmente: 18.008/941 em 2022; 18.248/738 em 2023; 17.740/591 em 2024; 17.358/553 em 2025; 7.106/219 em 2026 W1–7. Todos os números posteriores à W7 continuam fora deste diagnóstico. [População por ano](evidence/population.csv), [funil/joins independentes da v1](evidence/integrity_v1_reconciled.json). Foram reconstruídos os 84 artefatos científicos da referência em destino novo, com igualdade de bytes. Não houve redefinição da população nem download novo de PBP/FTN. Join completo não prova completude absoluta ou verdade dos rótulos.

## Integridade, cobertura e esquema

271 jogos REG em 2022, 272 em cada ano de 2023–25 e 107 em 2026 W1–7, exatamente os universos do calendário pinado. As chaves permanecem únicas, joins 1:1, sem rótulo elegível ou passer ausente. Sacks/scrambles, spikes, anuladas/no_play, conversões e POST continuam excluídos; throwaways, receiver desconhecido, overtime e penalidades com tentativa válida continuam presentes. Grupos de exclusão e contagens por semana/jogo/ID estão preservados na v1 e no replay local `reference-v1/build/audit/`.2022 tem menos linhas FTN fora do universo de passes elegíveis; isso não foi tratado como perda de rótulos elegíveis.

PBP tem 372 colunas em todos os cinco arquivos; `goal_to_go` muda int32→double em 2024–26, sem uso na baseline. FTN tem 29 colunas e os mesmos tipos Arrow em todas as temporadas, inclusive alvo bool. Estabilidade de schema não demonstra estabilidade semântica. Frequências de `read_thrown` revelam primárias NA em 2022 e código0 desde 2023; existe ` CHK` com espaço em uma linha de 2022. Campo não usado no modelo. [Comparação de esquemas](evidence/schema_comparison.json).

Manifestos conservam aquisição original da v1 em 04/11/2026, hashes e `date_pulled` disponível. `date_pulled` é a data em que jobs nflverse retiraram dados da API FTN, não data de anotação nem recibo de disponibilidade no kickoff. Há apenas uma revisão congelada por arquivo neste experimento; não estimamos alterações de rótulos entre revisões a partir de um snapshot único. Sem certificação histórica em tempo real. PBP2026 continua o congelado aprovado W1–7; FTN pinado tem W8 já exposta em agregados, nunca W9–13.

## Composição observada

[Composição completa](evidence/composition.csv): descida, distância, posição de campo, quarto, relógio, placar, profundidade, throwaway, penalidade, roof e presença de vento. Cada linha traz n, positivos, taxa, jogos e fração da população. Suporte descritivo n>=200 e positivos>=10; categorias abaixo disso não viram descobertas. As categorias de throwaway mantêm o nome/descrição pública, mas sua estabilidade operacional não foi certificada.

{ct}

A fração de passes profundos (20+) permanece perto de11,4–11,5%, enquanto a taxa FTN nesse grupo cai de12,56% a7,50% e6,54%. Isso é diagnóstico dentro de faixas, não prova sobre a causa. Throwaways passam de3,80% dos passes em 2022 a4,16% em 2025 e4,48% em 2026; a maioria dos rótulos é de não-throwaways. Não excluímos esses passes. A distribuição de relógio e situação de placar também está documentada, sem selecionar features novas.

Vento/temperatura presentes em34,58%,54,39%,63,04%,63,61%,41,09% por ano; cobertura depende de estádio/roof. Ausência não é zero. Dados de ambiente por estádio permanecem na auditoria v1 e são referenciados como disponibilidade, não mecanismos explicativos de mudança do alvo. Ambiente, profundidade e throwaway não entram em M0–M3.

## Composição comum predefinida

Principal: down2 × distância3 × campo3 × quarto2 × placar2 =72 células possíveis. Frequências de referência pooled2023–25; suporte exige pelo menos30 passes em **cada um dos cinco períodos**, sem usar positivos para excluir células. Restam39 células;33 removidas por suporte. Não houve retirada adicional por teto de peso5. As frações dentro do suporte são renormalizadas e os pesos são densidade referência/ano. Sem preenchimento de taxa de célula vazia, sem extrapolação e sem clipping de alguns indivíduos. Sensibilidade única mais grossa:8 células down2×distância2×placar2, todas com suporte e100% da população. [Contrato/células](evidence/standardization_contract.json), [principal](evidence/standardization_cells_primary.csv), [sensibilidade](evidence/standardization_cells_coarse.csv).

{st}

De2022 a2025, na população integral, queda de2,040 pontos percentuais. **No mesmo suporte principal**, queda crua de1,945 p.p. versus1,961 p.p. padronizada: ajuste amplia a queda em0,016 p.p. (fração associada à composição −0,83%). Sensibilidade completa:2,040 p.p. crua versus2,068 p.p. padronizada (diferença−0,028 p.p.; −1,39%). Até2026, no suporte principal,2,101 p.p. crua versus2,120 p.p. padronizada. Portanto, esta composição observada **não explica a queda**; não interpretar percentuais negativos como evidência causal de agravamento. São estimativas descritivas condicionadas às células/referência.

![Padronização](figures/standardization.png)

Limites: cerca de6–7% retirado na especificação principal; relógio, profundidade, defesa e diferenças contínuas dentro de células não são ajustados; referência e suporte são convencionais. Não há IC causal ou atribuição de parcela restante a anotadores/QBs. ESS e pesos são diagnósticos de estabilidade, não correção de variáveis omitidas.

## O que a documentação oficial confirma

[Loader FTN](https://nflreadr.nflverse.com/reference/load_ftn_charting.html): charting manual, subconjunto público desde2022, disponibilização informada em até48h e licença CC BY-SA4.0 com atribuição **FTN Data via nflverse**. [Agenda](https://nflreadr.nflverse.com/articles/nflverse_data_schedule.html): atualização FTN quatro vezes ao dia dependente do provedor; participação FTN pós2023 somente após a pós-temporada. Essas agendas não certificam completude de cada arquivo.

[Dicionário](https://nflreadr.nflverse.com/articles/dictionary_ftn_charting.html): alvo descrito somente como passe interceptável; não traz protocolo operacional detalhado ou concordância entre avaliadores. [Revisão oficial de01/09/2026](https://github.com/nflverse/nflreadr/commit/b32d434012) adicionou `n_defense_box` ausente no dicionário e detalhou `read_thrown`. O patch muda a ordem da linha do alvo, mas **mantém a mesma descrição**, não documenta alteração de critério de interceptável. O histórico do dicionário consultado tem introdução2023 e revisão2026; NEWS do pacote não documenta mudança de anotadores ou regra do alvo. Ausência de registro encontrado não prova ausência de mudança.

Fontes oficiais, patch e metadados de release foram congelados com URL/instante/hash em `additional-sources.json` e `provider-revision-source.json`. Não contatamos terceiros. Não sabemos qual parte da queda corresponde a jogo real, seleção não observada, execução, charting ou revisão. Tabelas/figuras FTN transformadas: CC BY-SA4.0, sem endosso; restrições de distribuição e limites jurídicos da [NOTICE v1](../qb-interception-risk-baseline-v1/NOTICE.md) continuam pertinentes.
''')
 diagnostics=table(['Ano','Modelo','Intercepto offset [IC95%]','Inclinação [IC95%]'],[[r['year'],r['candidate'],f"{r['calibration_diagnostic']['offset_intercept']:+.3f} [{r['calibration_diagnostic']['offset_intercept_ci'][0]:+.3f}; {r['calibration_diagnostic']['offset_intercept_ci'][1]:+.3f}]",'não identificável (constante)' if r['calibration_diagnostic']['slope'] is None else f"{r['calibration_diagnostic']['slope']:.3f} [{r['calibration_diagnostic']['slope_ci'][0]:.3f}; {r['calibration_diagnostic']['slope_ci'][1]:.3f}]"] for r in metrics])
 put('MODEL-CARD.md',f'''# Model card v2 — M3 escolhido para avaliação futura, sem validação final

Regra predefinida cumprida por M2 e M3 nos dois anos completos2024/2025. M3 tem menor LL pooled e é o único candidato contextual congelado para reserva. M0 e M1 continuam referências obrigatórias; M2 fica apenas auditável. [Protocolo](EXPERIMENT-PROTOCOL.md), [decisão completa](evidence/selection.json), [freeze](evidence/frozen/freeze.json).2025 e2026 W1–7 eram conhecidos antes desta rodada; não são novos testes.

M3 para2026: estrutura/contexto v1 em2023–24, C=.1, preprocessing só nesse treino. Offset de intercepto −0,1593395890254225 estimado em2025 separado, com estrutura e escalas imutáveis. Não houve refit da estrutura com2025 após calibrar. Features/sigmoide/JSON/solver são da v1. Sem profundidade, identidade, modelo de pressão, WP ou segundo alvo. Referência M1 usa553/17.358 da temporada2025. M0 usa estrutura original2022–25.

{metric_table}

{diff_table}

Pooled2024/2025, M3−M1 LL−0,00144896, IC95%[−0,00215155;−0,00077219]; Brier−0,00010782, IC[−0,00017580;−0,00004294]. Dois anos conhecidos apoiam uma utilidade contextual modesta além da referência recente. Seleção após examinar o histórico não é evidência confirmatória independente. Não avaliamos se a diferença entre M3 e M2 é estatisticamente conclusiva.

{diagnostics}

Intercepto offset ideal0; slope ideal1. Intercepto conjunto com inclinação também está no JSON. Constantes têm slope não identificável (null). Diagnósticos ajustados no período avaliado **não alteram** previsões nem selecionam recalibração pós-hoc. CIs usam2.000 reamostragens de jogos; todos os2.000 fits diagnósticos nos modelos reais foram válidos. Falhas/zero classes em fixtures produzem null e contagem explícita, não substituições falsas. Incerteza não inclui toda seleção/treino/verdade do rótulo. AP é average_precision_score, não área trapezoidal; ROC-AUC é complemento.

A correção de intercepto somente desloca probabilidades e preserva AP/AUC da mesma estrutura; essa igualdade é verificada executavelmente. `same_structure_before_offset_diagnostic` mostra os scores antes do deslocamento. M3 conserva discriminação relativa ao M1, mas isso não atribui efeito ao QB.2024 ainda superestima715,95 contra591, como M1 também superestima717,46; em2025 M1 está até mais perto em soma esperada (578,27 vs583,27), embora M3 melhore proper scores. Calibração futura pode falhar se o nível voltar a mudar.

Grupos com suporte suficiente não melhoram todos: M3 perde LL para M1 em distância1–3 de2024 (n1.782/y56; delta+0,000868) e roof fechado (n2.774/y109; +0,000078); em2026 Q1(n1.496/y45; +0,000452) e atrás9+(n1.525/y43; +0,001719). São diagnósticos, sem alegação de significância múltipla. [Todos os grupos](evidence/groups.csv).

Uso: pesquisa retrospectiva e candidato fixo para2026 W9–13. Não produção, ranking de decisão, culpa, causalidade ou habilidade persistente. Avaliação reservada pendente até maturidade, no mínimo16/12/2026 01:15 UTC (15/12 às22:15 em Fortaleza), se calendário não atrasar. [Guarda e exposição anterior](RESERVED-EVALUATION.md). Não foi aberta a reserva.
''')
 pos=table(['Classificação semanal agregada','IDs','Passes'],[[k,len(g),int(g.passes.sum())] for k,g in positions.groupby('position_class')]+[['unknown/conflicting',0,0]])
 put('REPORT.md',f'''# Diagnóstico temporal e calibração — entrega v2

**Estado A: diagnóstico concluído, M3 congelado para avaliação nova, reserva ainda pendente.** A composição contextual medida não explica a queda de prevalência. Uma constante recente resolve a maior parte do problema de nível da v1; M3 mantém uma vantagem retrospectiva modesta sobre essa referência. Isso não é validação final nem ranking de QBs.

## Achado retrospectivo: queda permanece com composição comum

De5,225% em2022 a3,186% em2025 (e3,082% em2026 W1–7). Nas39 células comuns, com93,2–94,0% de retenção e pesos máximos até1,317, a queda2022→2025 é1,945 p.p. crua versus1,961 p.p. padronizada. Especificação de8 células com100% da amostra produz2,040 versus2,068 p.p. Não estimamos parcela positiva explicada pela composição; mudanças observadas associam-se a diferenças muito pequenas e de sinal contrário. Não extrapolamos taxas para células ausentes. [Auditoria completa, exclusões, suporte e limites](DRIFT-AUDIT.md).

![Padronização](figures/standardization.png)

Não há mudança de schema FTN que explique mecanicamente os números; existe revisão documental de `read_thrown`/defense box, sem alteração documentada da definição do alvo. Não conhecemos estabilidade de anotadores/critério, revisões históricas ou causas da queda. Não atribuímos a parcela restante a melhora dos QBs nem a anotadores. O diagnóstico conserva alvo/população e todos os rótulos da v1.

## Referência recente e quatro candidatos delimitados

{metric_table}

M0 é a previsão v1 preservada. M1 é a prevalência da temporada anterior; M2 usa contexto da temporada anterior; M3 usa estrutura mais antiga e um ano separado para intercepto. Não houve novos algoritmos ou busca de C. O retrospecto comum foi fixado em2024/2025;2026 W1–7 não participa da escolha.

Em2025, o erro de contagem esperado−observado cai de181,47 em M0 para25,27 em M1 (redução descritiva de86,1% do excesso); em2026 de63,19 para7,39 (88,3%). M0 fica praticamente empatado com M1 em LL/Brier, mostrando por que a constante antiga da v1 era uma referência insuficiente. M3 acrescenta informação pequena porém consistente nos anos completos, sem depender somente de superar M0.

{diff_table}

![Diferenças](figures/performance_vs_recent.png)

M2 e M3 cumpriram a regra versionada; M3 teve menor LL pooled2024/2025 e foi escolhido. Delta LL pooled M3−M1−0,001449 [−0,002152;−0,000772]; Brier−0,00010782 [−0,00017580;−0,00004294]. A vantagem relativa pooled de LL é cerca de1,01%, não um grande salto. AP/AUC separam situações mais que uma constante. Não afirmamos superioridade estatística de M3 sobre M2; escolhemos pelo critério fechado. [Decisão](evidence/selection.json).

## Calibração: melhora de nível com limites

![Calibração](figures/calibration_known_periods.png)

![Diagnósticos](figures/calibration_diagnostics.png)

M3 em2025 prevê583,27/553 (p médio3,360% vs3,186%); em2026 W1–7 prevê226,12/219 (3,182% vs3,082%). Intercepto diagnóstico offset−0,055 [−0,143;0,029] e−0,033 [−0,183;0,109], respectivamente; slopes0,963 [0,683;1,243] e0,971 [0,564;1,346]. Isso é compatível com correção de grande parte do desvio conhecido, mas intervalos amplos não provam calibração individual ou futura.2024 ainda superestima. M1 constante tem slope não identificável; não lhe atribuímos slope0/1 artificial.

Apenas deslocar o intercepto não muda a ordenação ou AP/AUC da mesma estrutura; verificação passou. As melhorias de ranking versus M1 vêm da estrutura contextual; a adaptação corrige nível aprendido no passado. Nenhuma regressão diagnóstica de avaliação é aplicada às previsões. Faixas com n/positivos, intervalos e grupos estão nos [artefatos](evidence/metrics.json), [suporte das curvas](figures/calibration_support.csv) e [model card](MODEL-CARD.md). Há perdas em alguns grupos relevantes; não escondemos isso no agregado.

## Identidade e incerteza: apresentação separada da população

{pos}

Roster semanal2026 NFL.com via nflverse, adquirido e pinado nesta entrega, casado por **GSIS+temporada+semana+time**, apenas REG W1–7; não usamos posição atual fora do contexto como substituto. Campo `position` é a posição primária; `depth_chart_position` não foi tomado como verdade. São53 QBs identificados/7.097 passes e9 lançadores de outras posições/9passes; nenhum desconhecido/conflitante encontrado aqui, mas os casos são representados e testados. Todos62 continuam no dataset/modelos. [Classificação semanal](evidence/position_by_week.csv), [tabela interna alfabética](evidence/passer_presentation.csv), [dicionário oficial](https://raw.githubusercontent.com/nflverse/nflreadr/main/data-raw/dictionary_rosters.csv).

V2 **omite todos os intervalos comparativos por jogador**, inclusive com eventos. Zero positivos não permite interpretar bootstrap empírico degenerado como intervalo de risco/habilidade; poucos jogos, dependência e incerteza do modelo também comprometem os outros casos. Evidência v1 preservada, sem reescrita retroativa. Suporte e estimativas M0 continuam apenas para diagnóstico interno; sem ordenação pública de qualidade/decisão, sem hub visual ou modelo hierárquico novo.

## Reserva e confirmação independente

2025 e2026 W1–7 são conhecidos. W8 também teve agregados de rótulos expostos na v1, embora sem desempenho de modelo. Antes de novos rótulos, commit94e2b82 reservou **2026 REG W9–13**, sem escolha por positivos. M0/M1/M3 ficam fixos; não há métricas parciais, stopping favorável ou reajuste após abertura. Nenhum rótulo W9–13 foi adquirido/aberto neste trabalho.

Estado executado: **PREMATURE**, exit3, sem abrir PBP/FTN nem adquirir dados futuros. Último kickoff pinado08/12/2026 01:15 UTC; buffer de8dias implica não antes de16/12/2026 01:15 UTC (**15/12 às22:15 em Fortaleza**). Data é piso operacional condicionado ao calendário atualizado, scores completos e auditoria de todos os jogos/joins; não garantia de completude. Adiamento pode empurrar o piso; mudança de universo suspende abertura. [Protocolo reservado](RESERVED-EVALUATION.md), [recibo executado](evidence/reserved-status.json), [freeze](evidence/frozen/freeze.json).

## Reprodução, preservação e tentativas

V1 reconstruída com seu código inalterado em destino novo:84 arquivos científicos iguais byte a byte. V2 reconstruída offline em destino novo, incluindo a v1, modelos, splits e previsões. Igualdade de bytes, equivalência numérica e registro de ambiente são separados na verificação; não prometemos identidade entre BLAS/plataformas. Logs e saídas intermediárias ficam duráveis, sem sobrescrever referência. [Execução e recuperação](README.md).

Uma primeira chamada de replay foi feita antes de o preparo assíncrono criar o store; recusou o path de log e foi repetida após conclusão, sem ler dados. A primeira comparação completa da v2 encontrou120/124 arquivos iguais: os4SVGs diferiam por IDs de paths porque o renderer v1 alterou `svg.hashsalt` global no mesmo processo. Dataset/modelos/previsões/métricas e PNGs já eram idênticos. Corrigimos o estado local do renderer e repetimos **somente a etapa de figuras e comparação**, preservando a comparação falha; não afrouxamos tolerância nem retreinamos para melhorar resultado. O recibo final informa o resultado exato. Refinamentos de guardas (clock, manifesto, semanas, repetição de abertura, zero classe) não mudaram candidatos/regra ou métricas.

Produto, snapshots, backend, banco/ETL, v1 e servidor aprovado preservados. Sem Gemini/serviço pago/credenciais, terceiros contatados, merge/push/deploy/publicação, automação ou espera por semanas. Testes novos e v1, regressões legadas e hashes constam de [verificação](evidence/verification.json).

## Próxima ação

Revisar esta entrega; manter M3 e referências congelados. Quando a janela estiver madura, executar aquisição pública gated e **uma avaliação integral W9–13** com os comandos do README. Um resultado ruim deve permanecer registrado, não disparar tuning nesta reserva. Até lá, não promover residual contextual ao site ou a julgamento de decisão. Continuação: avaliação independente pendente, sem processo rodando à espera do calendário.
''')
 put('HANDOFF.md',f'''# Passagem v2

Resultado: **A — diagnóstico concluído, M3 candidato congelado e avaliação nova pendente**. O sinal é retrospectivo conhecido. Abrir [REPORT](REPORT.md), [DRIFT-AUDIT](DRIFT-AUDIT.md), [MODEL-CARD](MODEL-CARD.md) e [operação/reprodução](README.md).

- Base v1 d654bd65f834f3903006a97b3074123eda26d236 conferida limpa; documentos/código/347 artefatos pinados devem continuar intactos. Site aprovado5b38f04 e servidor18111 preservados. Não confiar em PID histórico.
- Reserva **W9–13**, decidida no commit94e2b82 por exposição agregada W8 na v1. Nunca consultamos novos rótulos dessa reserva. Conhecidos:2024/2025/2026 W1–7. Nenhum desses é holdout novo.
- Configuração científica em `experiment-verified/frozen` no store; arquivos também em evidence/frozen. M3 estrutura2023–24, calibração de intercepto2025, C=.1, offset−0,1593395890. M0/M1 preservados; não reabrir busca ou recalibrar com2026.
- Gate atual bloqueado até no mínimo16/12/2026 01:15 UTC (15/12 às22:15 Fortaleza), sujeito a calendário atualizado e janela completa. Não avaliar parcialmente nem criar automação. `acquire_reserved.py` recusa download prematuro; `reserved.py` valida relógio/manifests/código/contratos/joins antes de abrir rótulos. O recibo OPENED impede segunda abertura pelo mesmo bundle; preservar erro/recibo se houver falha, nunca apagar para tunar.
- Reprodução completa e backup durável verificados conforme recibos do README. Ambiente via lock/wheelhouse; nenhuma dependência em .env ou banco. Modelos são JSON, sem pickle.
-53 QBs identificados e9 outras posições; população mantém62 lançadores. V2 não emite IC comparativo por jogador. Zero eventos e pouco suporte não demonstram habilidade; classificação vem do roster semanal por GSIS, nunca nome.
- A composição comum praticamente não reduz a queda (no suporte principal2022→2025:1,945→1,961p.p.). M1 corrige muito do excesso; M3 agrega LL pooled−0,001449 vsM1 em2024/2025. Fonte/critério FTN e persistência de efeito individual continuam desconhecidos.

Próxima execução autorizável: aquisição pública após maturidade e avaliação integral, **sem mudar o procedimento escolhido**. Revisão técnica humana da v2 não foi presumida. Não houve produção/publicação. Hash de HEAD e commits devem ser lidos de git log; o documento não contém seu próprio hash.
''')
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--store',required=True);p.add_argument('--docs',required=True);a=p.parse_args();run(a.store,a.docs)
