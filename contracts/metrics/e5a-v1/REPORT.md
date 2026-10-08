# Relatório final E5a 1.0.0 — 08/10/2026

**Candidato à revisão do orquestrador. Contrato e exemplos concluídos; produção não implementada.**

Worktree: `/Users/pedrocollet/.codex/worktrees/metrics-contract-e5a/NFL Sideline`; branch `codex/metrics-contract-e5a`. Origem exata `6d99e66ccbe62861a7658dda67be51cf5773ff24` da branch integrada E4; não main. Commit do núcleo do pacote: `2abb2ee507098f2cf5942315441d9acbc3b8b46e`. Este relatório e o registro de verificação entram em commit local posterior; os hashes finais estão na resposta da entrega e no git log.

## Definições recomendadas

- **22 métricas**: EPA e success rate gerais/passe/corrida nos dois papéis; volumes elegíveis gerais/passe/corrida nos dois papéis; frequências de passe/corrida ofensivas e enfrentadas pela defesa. IDs, versão1.0.0 e fórmulas em [contract.json](contract.json).
- População `classified-scrimmage-v1`: pass/run finais, sacks no passe, scrambles na corrida; excluir kneel/spike/deleted/special/conversão, tratar flags desconhecidas explicitamente; conservar turnovers, OT, penalidades finais válidas e garbage time. Conversões excluídas são mudança versionada, não correção silenciosa do legado.
- EPA=`Σepa/epa_n`; SR=`success_n/epa_n`, EPA>0 estrito. Defesa significa **EPA/sucesso permitido ao ataque adversário**. Volume/frequência usam B elegível independente de EPA. Geral conserva soma/contagem próprias. Null e não finito nunca viram zero.
- Persistência proposta por **jogo/revisão**, suficiente para filtrar cada evento e depois agregar; semanal apenas como rollup. Temporada até corte e últimas três semanas NFL recomendadas, sem alongar recência para preencher bye/lacuna. Últimos três jogos são janela distinta/opcional.
- Corte de segundos em UTC, próprio jogo excluído por ID, eventos sem bound de encerramento comprovado excluídos de recorte certificado. asOfDate mapeia ao início da data UTC. `EVENT_RECONSTRUCTION` e `POINT_IN_TIME` têm garantias diferentes; disponibilidade de bytes não é gameday.
- Cobertura por calendário/revisão fixa, fonte e fundamento; volume, exibição/comparação e incerteza separados. Nenhum limiar estatístico/confiança proposto; uma observação pode ser exibida descritivamente com ressalva.

## Divergências e evidência

O [inventário](INVENTORY.md) registra cálculo, filtros, populações, numeradores/denominadores, unidades, granularidade, ausências e consumidores. Divergências principais:

1. `dropback_rate`/catálogo anunciam dropback, mas o loader usa pass classificado entre EPA presentes; scrambles permanecem em run.
2. N(P/R), somas e sucessos por fundamento não são persistidos; `EvidenceWindow` usa média simples de médias específicas, corretamente rotulada como não ponderada, insuficiente para nova temporada ponderada.
3. Chave semanal perde jogo/fase; `asOfDate` não filtra consulta; últimas três linhas disponíveis não equivalem a últimas três semanas ou jogos.
4. Inner join elimina time-semana unilateral; ausência não identifica bye/falha/atraso; upsert não apaga média velha se nova revisão não cria linha.
5. Legado não valida finitude, duplicatas, conversões, deleted/special ou flags desconhecidas; early_down/explosive têm coluna e catálogo, mas não produtor comprovado.
6. Snapshot v1 é subconjunto sem novos denominadores/recortes; E4 não corrigiu os defeitos de cálculo/tempo da comparação pública.

Os Parquets **já existentes** de2023/2025/2026 foram lidos sem aquisição. Contagem de base cai de35.600→35.474,34.632→34.502 e3.835→3.830 pela exclusão de126/130/5 conversões. Não há outras diferenças nesse predicado local, mas completude, bounds e receipts não foram certificados. Hashes, schema, versões e exemplos em [proveniência](PROVENANCE.md) e [local-audit.json](local-audit.json). Links oficiais e inferências estão registrados; versão do modelo de EPA dos arquivos continua desconhecida.

## Verificação executada

- `python3 contracts/metrics/e5a-v1/verify.py`: **26 casos golden aprovados**, incluindo três rejeições esperadas.
- `python3 -m unittest discover -s contracts/metrics/e5a-v1 -p 'test_*.py' -v`: **23 testes aprovados**. Permutação, partição/reunião, soma ponderada, reconciliação ataque/defesa, amostra específica, futuro/próprio jogo, disponibilidade, cobertura monotônica, null/zero/tiny, fase/temporada e duplicatas/conflictos.
- Auditoria opcional `probe_local.py` com Polars instalado: três PBP e três schedules lidos; JSON versionado. Nenhum pipeline ou main de loader executado.
- Python AST e JSON válidos; links locais do pacote conferidos; `git diff --check` e diff staged sem erros. Alterações confinadas a `contracts/metrics/e5a-v1/`.

O ledger manual demonstra EPA ponderado **−0,125** versus média das médias **+0,083333…** no mesmo conjunto de oito jogadas. Isso prova diferença mecânica, não seleção ótima de janela nem acurácia preditiva. Os testes foram pertinentes ao pacote novo; suítes Java/frontend/ETL de produção não foram repetidas. [Registro estruturado e hashes](verification.json).

## Lacunas reais e próximo pacote

Receipts históricos por bytes, fim/ordem dos eventos, completude por jogo e versão do modelo de EPA não estão comprovados nos arquivos locais. Sem evidência, conservar UNKNOWN/exclusão, não fabricar availableAt ou fim de jogo. Unicidade game/play foi observada nesses arquivos, mas exige guard envolvendo drive no futuro backfill. Compreensão humana E4 e avaliação independente continuam pendentes.

Após revisão do orquestrador, iniciar **E5b-1: adapter e somas puras offline por jogo**, com join PBP/calendário, fase/round, validação de IDs/flags, dedup e conflitos, contagens/somas por papel/fundamento e CLI dry-run para diretório de revisão. Saída deve reconciliar os ledgers E5a e as conversões dos locais, mantendo completude desconhecida quando não comprovada. Migration/proveniência, corte/janelas, leitor/contexto Java e backfill seguem pacotes separados com critérios de saída em [E5B.md](E5B.md).

Nenhuma alteração em ETL de produção, migrations, motor editorial, contextos/artefatos históricos, E1, snapshots, aprovações, frontend ou BASIC/FULL. Sem .env, banco remoto/credenciais, Gemini/modelos, aquisição de datasets, push, deploy ou merge em main. A worktree de origem e seus arquivos não rastreados foram preservados.
