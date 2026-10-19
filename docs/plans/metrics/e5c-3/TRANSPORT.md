# Contrato interno de transporte — v1

Perfil fechado implementado em `metrics_lab.adapter` e em
`web-ui/local-editorial/observations/model.ts`. Sem mudança nos contratos aceitos.
A tabela descreve campos obrigatórios; objetos não admitem campos extras no
cliente. `null` significa indisponível e não pode virar `0`.

| Objeto | Conteúdo e semântica |
|---|---|
| configVersion | `metrics-lab-config-v1`; bundles nominais, sem descoberta/latest |
| entrada do operador | entryId slug único, label seguro, dataKind REAL_ARCHIVE/SYNTHETIC, path absoluto, expectedBundleId obrigatório |
| snapshotVersion | `metrics-lab-snapshot-v1`, saída interna do filho Python; não há entrada para snapshot salvo |
| sessionId | SHA-256 do snapshot canônico completo, sem o próprio campo; inclui estados de erro, labels e todos os DTOs |
| catálogo transportVersion | `metrics-lab-catalog-v1`; sessionId, errorCode e bundles |
| entrada do catálogo | entryId, label, dataKind, status READY/ERROR, bundleId, errorCode, observations; ERROR tem documentos vazios e bundleId null |
| resumo | observationId, dtoId, subject, request; suficiente para seleção nominal |
| resposta transportVersion | `metrics-lab-response-v1`; sessionId e document |
| document dtoVersion | `metrics-lab-observation-v1` |
| identidade do documento | entryId, bundleId, observationId preservados; dtoId identifica **o DTO reduzido**, não os bytes originais |
| subject | team, role off/def, foundation general/classified_pass/classified_rush |
| request | season, phase REG/POST, origin CURRENT/HISTORICAL_REFERENCE, period DECLARED_WEEKS e weeks |
| observed | actualWeeks e includedGameIds; fonte presente vazia pode ser observada, ausência não entra na soma |
| totals | null sem fonte para soma; ou eligibleN, epaN, successN, epaMissingN, epaNonfiniteN, generalEligibleN, unknownFilterFlagsN, epaSum |
| values | epa, successRate, volume, frequency; cada um null ou {numerator,denominator} |
| guarantees | estados/motivos independentes de integrity, coverage, completeness, compatibility e temporal; coverage inclui expectedCount/coverageRatio; compatibility inclui epaModel |
| members | gameId/week/round/sourceState/completeness/statistics; sem associações/receipts completos |
| limitations | lista de code e subjectId seguros; não resumir ou eliminar motivos obrigatórios |
| fieldScopes | textos literais do contrato operacional E5c-2: origem dos contadores, especialmente flags de contexto de jogo |
| presentation | epaDecimals, ratePercentDecimals, rounding HALF_UP |
| scope | aggregation NO_OBSERVATION/SINGLE_GAME/MULTI_GAME; population OBSERVED_SAMPLE/DECLARED_POPULATION |

Contagens e denominadores são strings de inteiros canônicos não negativos;
somas EPA e numeradores preservam decimais exatos canônicos. Season/week continuam
inteiros pequenos. Não reconstruir contagens a partir de percentuais. Frequência
só existe para passe/corrida com general da mesma população/revisões. Defesa
conserva números e passa a usar rótulo permitido. Não somar observações sobrepostas.

`scope.aggregation` classifica contexto: sem jogos com fonte é NO_OBSERVATION;
um único membro é SINGLE_GAME; demais são MULTI_GAME, inclusive quando parte dos
membros não tem fonte. DECLARED_POPULATION requer cobertura KNOWN e completude
COMPLETE; não significa suficiência estatística. unknownFilterFlagsN replica
somente a contagem já derivada pela E5c-2, uma vez por jogo **dentro daquela
observação**; não é medida de time/fundamento nem aditiva entre observações.

Perfil de apresentação aceita 0..12 casas para limitar recursos/UI. Essa é uma
restrição explícita do transporte, não limiar estatístico nem alteração de
observation-v1. Identificadores de modelo fora do perfil seguro ou campos que
não possam ser preservados provocam erro da entrada, sem renomear/truncar dados.

## Responsabilidades na fronteira operacional

O reader Python E5c-2 verifica bytes/hashes, identidades e seleção nominal,
originais completos, associações, receipts, reconciliação e rederivação. Ele
recusa adulteração seguida de rehash externo. O adaptador apenas reduz os dados
aceitos, verifica pin e perfil e não concede novas garantias. O registro
REAL_ARCHIVE é declaração explícita do operador, não autenticação de terceiros;
fixtures reconhecíveis não podem receber esse rótulo.

O processo usa execFile sem shell, argv fixo, ambiente mínimo; paths/executável
são somente do operador. Limites: 120 s, 8 MiB de saída. Uma preparação falha
retorna código sanitizado, sem stderr/tracebacks. Requisitos de perfil falham por
entrada; configuração inteira inválida/subprocesso falho tornam catálogo
indisponível. Não buscar dados pela rede.

O plugin valida a estrutura e congela **strings JSON** privadas. O browser
verifica versões, campos, contagens/razões, períodos, limites e fieldScopes,
identidades do índice e da resposta; isso não autentica fontes nem substitui o
reader. IDs opacos ligam DTO → observationId → bundle validado para auditoria
offline; a linhagem integral permanece fora do browser.

## HTTP e atualização

GET `/__observations/` e GET `/__observations/{entryId}/{observationId sem sha256:}`.
Host `127.0.0.1:18083`, Origin ausente ou exatamente a mesma origem, marcador
`X-Local-Observations: 1`. Sem corpo, query, encoding de path ou outros métodos.
Documento exige `X-Observation-Session` igual ao catálogo. 403 para requisição
recusada; 404 para documento inexistente; 409 para sessão divergente. Catálogo
retorna 200 com erro explícito por entrada/configuração. Respostas no-store e
nosniff. Não há POST/reload que execute Python, gere observações ou publique.

Mudança do bundle no disco não altera bytes já congelados. Reinício executa de
novo a validação e substitui catálogo/documentos como uma unidade. Identidades
iguais indicam mesmo conteúdo, não uma nova garantia temporal. Preferência do
browser contém apenas entryId/observationId. Cancelamento e conferência de
identidades descartam respostas atrasadas; escolha removida produz aviso sem
selecionar outro bundle.

## Garantias e linguagem

Completude UNKNOWN, modelo UNKNOWN e conhecimento temporal UNKNOWN não apagam
observações reconciliadas. Permanecem visíveis período, denominadores, amostra,
modelo não identificado e conhecimento no corte não demonstrado. Cobertura
esperada UNKNOWN não gera percentual. Fonte ausente, fonte presente sem jogadas,
COMPLETE vazio, valor zero e denominador zero são estados distintos.

Este perfil aceita somente temporal UNKNOWN, inclusive dados com alvo incluído;
não cria elegibilidade pregame. Compatibilidade básica CONFLICT é recusada.
Semanas iguais não alinham cortes: não existe operação de comparação neste modo.
Não há eixos comuns, diferenças, ranking, melhor/pior ou frase de superioridade.
As três correções do aceite E5c-1 permanecem protegidas, sem implementar PIT aqui.
