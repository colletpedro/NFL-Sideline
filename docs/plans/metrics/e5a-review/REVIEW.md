# Revisão do orquestrador — E5a, 08/10/2026

**Decisão: adotar as definições como base de E5b-1, com a errata obrigatória abaixo.** Não é aceite do verificador como adapter de PBP bruto, nem implementação das métricas no produto. O pacote candidato 1.0.0 permanece intacto, incluindo seus hashes e status original; esta decisão é posterior e deve acompanhar o handoff.

Base de integração: `6d99e66ccbe62861a7658dda67be51cf5773ff24`. Pacote recebido: `2abb2ee507098f2cf5942315441d9acbc3b8b46e` e `5e976a315a167795222061175e582148bc570c33`. Branch local de revisão: `codex/metrics-integration-e5a`; main não recebeu merge.

## Definições adotadas

- População classificada versionada: sacks em passe, scrambles em corrida, conversões excluídas. Frequência classificada tem identidade própria; não reutiliza a definição legada de dropback_rate.
- Eficiência usa somente EPA finito e denominador do respectivo fundamento; success rate usa EPA estritamente positivo. Defesa conserva EPA/sucesso permitido, sem inverter o sinal.
- Volume/frequência não dependem de EPA disponível. Agregação conserva somas e contagens por jogo/revisão; médias semanais não são estatísticas suficientes.
- Temporada acumulada e últimas três semanas NFL são recortes separados. Bye não estende janela; referência histórica não preenche ausência corrente.
- Corte por evento e disponibilidade dos bytes são garantias distintas. Instante, disponibilidade, ingestão, completude e versão do modelo desconhecidos continuam explícitos.
- Cobertura, volume e elegibilidade descritiva não representam confiança estatística. Não há previsão de vencedor ou amostra mínima estatística validada.

## Errata obrigatória: validação de linhas fora da população

`verify.py::normalized_plays` exige posteam/defteam não nulos em **todas** as linhas, antes de `aggregate` excluir tipos fora de pass/run. `evaluate` também compara os dois times em todas as linhas. Entretanto, há linhas do PBP bruto fora dessa população com ambos os campos nulos. O candidato sintético passa; a aplicação direta do mesmo normalizador aos arquivos reais falha.

| Temporada local | Linhas brutas | Fora de pass/run | Fora de pass/run com ao menos um time nulo | Pass/run com time nulo |
| --- | ---: | ---: | ---: | ---: |
| 2023 | 49.665 | 14.065 | 2.638 | 0 |
| 2025 | 48.771 | 14.139 | 2.729 | 0 |
| 2026 | 5.489 | 1.654 | 297 | 0 |

A inspeção foi somente leitura de arquivos já existentes. A reprodução mínima, independente desses Parquets, está em [reproduce_boundary.py](reproduce_boundary.py); os resultados estão em [verification.json](verification.json). O dicionário oficial documenta inclusive linhas com play_type ausente fora de jogadas classificadas: [nflreadr PBP](https://raw.githubusercontent.com/nflverse/nflreadr/master/data-raw/dictionary_pbp.csv). Isso sustenta separar o formato bruto da população, sem relaxar a validação dos candidatos.

Para E5b-1, a fronteira fica definida assim:

1. Validar schema, identidade do jogo/jogada, season/phase/week e vínculo com calendário; detectar duplicatas/conflitos no conjunto bruto, incluindo linhas excluídas. Não simplesmente apagar linhas fora da população antes da auditoria.
2. Classificar o tipo. Linhas fora de pass/run são excluídas e auditadas por jogo. Nelas, posse/defesa ausentes não invalidam o lote e não são preenchidas com times inventados. Validar valores estruturais presentes; ausência de campos específicos da eficiência nessa linha não cria observação.
3. Em candidatos pass/run, exigir os dois participantes distintos e reconciliados com calendário, aplicar flags/filtros e validar EPA conforme a política de finitude. Time ausente/trocado continua sendo erro, não exclusão silenciosa.
4. Separar contagem bruta/única e exclusões por jogo das contagens atribuídas a time/papel. Uma linha sem posse não deve ser artificialmente debitada a uma das equipes. A reconciliação off/def refere-se às mesmas jogadas elegíveis.
5. Preservar no manifesto a população bruta usada para conferir contagens. Filtrar antes de comparar `expected_unique_rows` produziria um falso diagnóstico de fonte parcial.

Esse ajuste não muda a classificação, os 22 IDs, fórmulas, denominadores ou a exclusão de conversões. Corrige a fronteira entre entrada bruta e observação elegível. O verificador E5a é um modelo limitado de exemplos; não deve ser copiado como adapter nem usado para certificar entradas que não modela.

## Alcance da verificação

Reexecutados: 26 exemplos (incluem três rejeições esperadas), 23 testes, reconciliação dos 12 hashes do pacote e `git diff --check`. Conferidos diretamente o predicado legado e a consulta Java: frequência legada condicionada a EPA, médias específicas sem denominadores e asOfDate registrado sem filtrar a consulta. Fontes primárias do PBP e calendário foram consultadas novamente; elas não certificam os bytes históricos locais.

Acrescentada reprodução independente da falha de fronteira: fora da população + times nulos é rejeitado pelo modelo atual; o controle pass/run + time nulo também é rejeitado, e deve continuar assim no adapter. Não foram reexecutadas suites Java/frontend, pois não houve alteração de runtime. Testes mecânicos não provam qualidade editorial, completude de dados ou reconstrução histórica.

## Próxima entrega: E5b-1

Implementar somente adapter offline, join calendário/PBP, auditoria e somas por jogo/papel/fundamento, com CLI dry-run em diretório novo. Ler conjuntamente o [contrato candidato](../../../../contracts/metrics/e5a-v1/CONTRACT.md), o [handoff E5b](../../../../contracts/metrics/e5a-v1/E5B.md) e esta errata.

Critérios adicionais de aceite: fixture bruta contendo linhas fora da população com times nulos; rejeição de candidatos sem time ou com participante errado; dedup/conflito também nas linhas excluídas; contagem de manifesto antes dos filtros; igualdade do resultado sob permutação; reconciliação com os ledgers e exclusões de conversão 126/130/5 nos arquivos opcionais com os mesmos hashes. O core precisa ser reproduzível sem Parquets ignorados.

Completude UNKNOWN não impede calcular estatísticas do **conteúdo presente**, mas esses resultados devem ser separados e rotulados como subset auditável; não serão volume do jogo completo nem observações COMPLETE. Contagem consistente e scores preenchidos, por si, não certificam completude. Sem prova de encerramento/disponibilidade não emitir garantia pregame ou POINT_IN_TIME.

Seleção entre revisões, calendário recebido/ingerido antes do corte, DST e comprovação de receipts ficam para E5b-3; o modelo E5a não implementa essas garantias integralmente. Migration, writer, ETL principal, Java, backfill, visual e publicação continuam nas entregas posteriores. Não é necessário reabrir a definição das métricas para iniciar o adapter com esta errata.

E4 continua com compreensão humana/amostra independente pendentes. BASIC/FULL, as cinco falhas legadas e a evolução pública continuam abertas. Nenhuma alteração no candidato congelado, histórico, .env, banco, aquisição, snapshots, frontend, main ou Production; sem push/deploy.
