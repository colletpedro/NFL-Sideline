# Contrato candidato `metrics-auditable-observation-v1`

## Origem e fronteira

Documento interno distinto de `metrics-temporal-result-v3`, PIT, claims e contrato
visual v1. `policyVersion=metrics-consumption-policy-v1` e
`derivationVersion=metrics-observation-projection-candidate-1` são versões de
**desenho**, não um componente implementado. Fonte permitida:
`OFFLINE_PERSISTED_ACCEPTED`, via statistics/game-audit/reconciliation/manifest
E5b-1 e associações/artefatos/bytes E5b-2, validados pelo caminho de recuperação
E5b-4/identidades. Nunca ler números de PIT sem agregados; nunca trocar PIT por
retrospectivo ou afrouxar seu corte. Observação arquivada não requer tempo de
encerramento demonstrado; ela informa exatamente essa falta.

O schema descreve uma projeção de **um grupo** time/papel/fundamento e seus
membros por jogo, não duplica os 12 grupos ou a fórmula E5a. Catálogo autoritativo:
`../e5a-v1/contract.json` (22 IDs, definição 1.0.0, população
classified-scrimmage-v1). Um fundamento general não possui frequency. Relações
pass+run/off=def devem ser verificadas sobre os originais completos antes da
projeção, não reconstruídas a partir de um grupo isolado.

## Campos e identidades

Todos os campos do schema são obrigatórios e fechados; null tem semântica
explícita. Arrays de conjuntos são ordenados e únicos no documento emitido.
Strings de decimais são finitas, sem expoente, canônicas (sem zeros finais ou
zero negativo). Contagens inteiras não negativas. IDs antigos permanecem literais.

| Campo | Semântica / validação necessária |
|---|---|
| observationId | SHA-256 do JSON UTF-8 canônico de todos os campos, exceto observationId, presentation e derivedAt. Objetos ordenados por chave, separadores compactos, ensure_ascii=true, nenhum float; conjuntos ordenados por ID. Política/garantias/limitações entram na identidade |
| derivedAt | tempo de derivação, UTC com segundos; nunca conhecimento no corte; mudar este campo não muda identidade semântica |
| definition | definitionVersion, populationVersion, adapterVersion; papel off/def, fundamento general/classified_pass/classified_rush estão em subject; unidades e direção vêm do catálogo |
| subject | team, role, foundation; defesa conserva EPA e success rate **permitidos ao ataque adversário**, volume/frequência enfrentados; não inverter sinal nem usar 1−SR |
| request | season, phase REG/POST, origin CURRENT/HISTORICAL_REFERENCE, period {kind: DECLARED_WEEKS, weeks}; selectionManifestId preserva a escolha nominal e sua regra de seleção transparente, sem inferir janela temporal. Inventário nominal com calendarSourceSetId. Não é janela temporal aceita nem SEASON_TO_CUTOFF. Season completa só com suporte próprio e lista explícita de semanas |
| observed | actualWeeks, includedGameIds; apenas jogos com fonte estatística presente, inclusive vazia; metricUsedGameIds por família, nunca confundir jogo observado e denominador EPA |
| members | gameId, week, round preservada, sourceState PRESENT/ABSENT, sourceRevisionIds, calculationId, coverageRevisionId, artifactId, archiveReceiptIds, completeness, statistics; uma cobertura escolhida nominalmente por jogo. Ausente não recebe grupo estatístico nem calculationId/artifactId |
| statistics | eligibleN, epaN, epaSum, successN, epaMissingN, epaNonfiniteN, generalEligibleN, unknownFilterFlagsN; dados de B e E E5a, general do **mesmo** jogo/papel/revisões |
| totals | somas exatas dos membros presentes; null se nenhuma fonte, não zeros fabricados. Soma EPA null iff epaN=0; eligible=epa+missing+nonfinite; success≤epa. generalEligible≥eligible; general exige igualdade |
| values | epa, successRate, volume, frequency; null ou {numerator: decimal string, denominator: inteiro positivo}. EPA=soma/epaN; SR=successN/epaN; volume=eligibleN/1; frequência=eligibleN/generalEligibleN. Fração não precisa ser reduzida; denominador de auditoria preservado |
| guarantees | sourceModels vincula estado/modelId/evidenceIds a cada FILE utilizado; um modelo de lote não promove FILE desconhecido. Cinco dimensões independentes conforme GUARANTEES; cada estado tem reasonCodes e evidenceIds. expectedGameIds/count/coverageRatio são null se expectativa não provada; observed/used não dependem disso |
| limitations | {code,subjectId} ordenados e únicos; código vinculável ao motivo/ID afetado, sem texto livre promovido a prova |
| presentation | epaDecimals, ratePercentDecimals, rounding HALF_UP; configuração excluída do observationId. Padrão recomendado E5a 3/1; outras casas não alteram dados/sinais |

Arquivo/SET, lote, cobertura, associação, receipt e revisão temporal são
identidades distintas. Novo observationId identifica somente esta derivação.
`members` retém todos os lotes necessários pela escolha nominal; cobertura
compartilhada conta uma vez por jogo. Alternativas e réplicas ficam no arquivo de
linhagem original referenciado, não viram membros adicionais. Mesmo ID proprietário
com bytes divergentes é erro estrutural, não UNKNOWN. Dois membros do mesmo jogo
com revisões diferentes são escolha ambígua e invalidam este documento.

`integrity.evidenceIds` deve apontar a hashes e relatório de reconciliação
aceitos sobre os bytes originais e vínculos completos. A futura projeção precisa
entregar um bundle fechado de linhagem (originais ou locators locais resolvíveis
com hashes) para auditoria; somente strings de IDs não provam integridade.
Este pacote sintético usa IDs sha256 de conteúdo sintético e não representa
archives operacionais. O verificador não autentica esses IDs como documentos reais.

## Ausência, vazio, zero e subset

| Caso | Fonte / contagens / valores / descrição mínima |
|---|---|
| Jogo sem fonte | ABSENT, revisions=[], statistics=null; cobertura de calendário pode existir, sem grupo fabricado. Mostrar lacuna, números desconhecidos |
| Fonte presente vazia UNKNOWN | PRESENT com revisão, eligible=epa=0, soma null. Volume observado 0, eficiência/frequência null. “0 jogadas elegíveis nos bytes observados; completude desconhecida” |
| Subset observado | PRESENT, completude PARTIAL ou UNKNOWN. Somas/contagens somente dos bytes; jamais “total do jogo/temporada” |
| COMPLETE vazio | PRESENT, counts=0 e prova aceita sobre aquela população/revisão e calendário. “População declarada completa sem jogadas elegíveis”; não implica EPA zero |
| Denominador zero | valor null, motivo NO_EPA_OBSERVATIONS ou ZERO_FREQUENCY_DENOMINATOR; fonte pode existir e volume ser positivo |
| Valor zero válido | numerator='0', denominator>0; EPA zero ou SR zero são números conhecidos, sem imputação |
| Valor desconhecido | null com SOURCE_UNKNOWN/NO_SOURCE_OBSERVATION ou motivo específico; ausência nunca cria zero/COMPLETE/bye |

EPA desconhecido por falta de valores não apaga volume/frequência de B.
Modelo UNKNOWN não apaga EPA observado reconciliado: exige rótulo junto ao dado
“EPA da fonte, modelo não identificado”, incluindo EPA-dependência do SR.
Ausência de modelo impede equivalência, direção de qualidade e comparação de
EPA/SR. Modelo conhecido diferente nunca se agrega; formar observações separadas.
Não misturar conhecidos e UNKNOWN numa média com modelo implícito. Não misturar
fases/temporadas/populações. Período observado retém lacunas, não busca outra semana.

Cobertura de jogos observados é distinta de cobertura de jogadas EPA. Se esperado
é conhecido por revisão/declaracão aceita, coverageRatio=|includedGameIds|/expectedCount
(denominador zero => null). expectedCount=null => ratio=null mesmo se existem
272 IDs no calendário arquivado; pode-se mostrar “272 jogos observados / 272 IDs
no inventário”, sem anunciar taxa de cobertura da população esperada.

## Exatidão e texto mínimo

Somar Decimal/Fraction a partir das somas E5a preservadas; não somar float,
arredondar intermediários, fazer média de médias ou recuperar contagens de taxas.
O schema guarda razão exata, não string de número formatado. Na UI futura, EPA
3 casas HALF_UP, taxas 1 casa percentual; não zero que arredonda a zero usa sinal
e desigualdade E5a (+<0,001, −<0,001, <0,1%). Mostrar fração/contagens no detalhe.
Número de jogos/semanas não substitui epaN. Volume/frequência não são eficiência.

Texto defensável com UNKNOWN: “Nos bytes arquivados de [temporada/fase/semanas],
[time/papel] teve N jogadas elegíveis; EPA da fonte S/E em E observações, [EPA
permitido se def], modelo não identificado, completude e conhecimento no corte
desconhecidos”. Não usar “média da temporada”, “forma atual”, superioridade,
causa, vantagem ou pregame. Limitações, período e denominadores precisam ficar
próximos do ponto/série, inclusive em exportação/captura; tooltip sozinho não basta.

Em exemplos sintéticos, `synthetic-other-population-v1` representa um segundo
perfil hipotético validado, para testar incompatibilidade, não população suportada
pelo adapter aceito atual. A projeção operacional futura deste caminho só emitirá
classified-scrimmage-v1 até aceite explícito de outro adapter/população.
