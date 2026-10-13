# Matriz de garantias independentes

Estados são qualificações condicionais a uma política explícita de origem,
responsável e vínculo aceitos; não autenticam o fornecedor. UNKNOWN significa
não demonstrado, não falso nem zero. Cada dimensão conserva motivos e evidenceIds.
Ausência de documento => UNKNOWN + motivo; declaração não aceita => UNKNOWN +
DECLARATION_UNPROVEN. Conflito material não é resolvido escolhendo a declaração
conveniente. Integridade quebrada invalida o pacote; conflito de declarações
bloqueia só as operações que precisam da dimensão, preservando bytes íntegros.

| Dimensão / estados | Evidências necessárias | Limites / operações |
|---|---|---|
| Integridade: RECONCILED, UNKNOWN, CONFLICT | Identidade de jogada, jogo, fonte/revisão e versões; hashes de bytes/artifacts/receipts conferidos; manifesto integral, associação por jogo, contagens/somas/exclusões e linhagem reconciliadas pelo caminho aceito | RECONCILED permite exibir valores de subset. Não prova autenticidade, completude, modelo ou tempo. UNKNOWN recusa pontos numéricos derivados; pode exibir indisponibilidade. CONFLICT aborta documento numérico; não converte em subset |
| Cobertura: KNOWN, PARTIAL, UNKNOWN, CONFLICT | População esperada definida e comprovada independentemente do PBP; IDs esperados/observados/usados e razões de lacuna; versão/completude de calendário e, se corte, classificação dos eventos/fechamento de semanas. KNOWN=expectativa provada e todos esperados observados (inclui zero esperado); PARTIAL=expectativa provada com lacunas; UNKNOWN=denominador não demonstrado | A taxa de fonte usa todos esperados, inclusive sem PBP; usos por métrica são listas separadas. KNOWN não prova completude dentro do jogo. UNKNOWN mantém expectedIds/count/ratio null, mas lista observados/usados. CONFLICT recusa taxa e comparação de período; só observações individuais reconciliadas |
| Completude: COMPLETE, PARTIAL, UNKNOWN, CONFLICT | Declaração com autoridade/política, população, revisão e bytes exatos, suporte auditável de que a fonte representa toda a população declarada; inventário e controle de omissões. PARTIAL exige evidência de subset, não mera suspeita | COMPLETE não é inferido por quantidade de jogos, sucesso ETL, placar, hash, revisão mais recente ou ausência de gaps. PARTIAL e UNKNOWN permitem observação como amostra; recusam comparação do período e pregame. CONFLICT permite observação do conteúdo, sem escolher qual declaração é verdadeira |
| Compatibilidade: KNOWN, UNKNOWN, CONFLICT | Definição, unidade, população, papel, fundamento, season/phase/origin, assinatura do período e método de soma/denominador. Modelo EPA por todos os arquivos: KNOWN com ID, UNKNOWN com null, CONFLICT com null/motivos | É por família/par, nunca selo global. Volume/frequência independem do modelo; EPA/SR dependem dele. KNOWN local não garante que outro documento coincide. UNKNOWN/conflito nos campos básicos recusa alinhamento/diferença; números íntegros conservam descrição literal. Modelos diferentes ficam separados |
| Conhecimento temporal: KNOWN_AT_CUTOFF, UNKNOWN, NOT_KNOWN_AT_CUTOFF, CONFLICT | Corte exclusivo, prova de disponibilidade/ingestão de cada revisão/recurso/dependência e recebimento das declarações < corte; FINAL e bound aceitos; calendário e fechamento necessários. Prova de kickoff pregame separada | Tempo retrospectivo de evento não é conhecimento. Receipt atual e persisted_at não promovem histórico. UNKNOWN/NOT_KNOWN/conflito permitem exibição arquivada e, se outros requisitos passarem, comparação descritiva. Recusam pregame; equality com corte também recusa |

Motivos mínimos: INTEGRITY_UNPROVEN, IDENTITY_CONFLICT, LINEAGE_UNRECONCILED;
EXPECTATION_UNKNOWN, EXPECTATION_CONFLICT, INCOMPLETE_SOURCE_COVERAGE;
COMPLETENESS_UNKNOWN, SOURCE_SUBSET, COMPLETENESS_CONFLICT;
INCOMPATIBLE_DEFINITION_OR_POPULATION, MISMATCH_REQUESTED_PERIOD,
EPA_MODEL_UNKNOWN, INCOMPATIBLE_EPA_MODELS_SEPARATED;
AVAILABLE_AT_UNKNOWN, INGESTED_AT_UNKNOWN, EVENT_TIME_UNKNOWN,
EVIDENCE_NOT_KNOWN_AT_CUTOFF, TEMPORAL_DECLARATION_CONFLICT.
Os códigos já aceitos de E5b-3 são preferidos. Novos códigos locais de apresentação
não mudam a semântica de razões congeladas.

Não ordenar as cinco dimensões como níveis sucessivos. Exemplo: integridade
RECONCILED, cobertura KNOWN, completude UNKNOWN, modelo UNKNOWN, conhecimento
UNKNOWN é válido e exibível. KNOWN de cobertura com zero esperado não gera taxa
100%; média sem denominador continua null. Garantia depende do conteúdo/prova,
nunca de rótulo “completo”, cor verde ou renomeação de categoria.
