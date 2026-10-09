# Aceite do orquestrador — E5b-1, 09/10/2026

**Aceita no escopo offline.** Adapter, CLI, estatísticas suficientes e auditoria incorporados à branch local `codex/metrics-integration-e5b1`. Não foi necessária correção de runtime nesta revisão. Main, histórico, pipeline principal e consumidores públicos permanecem intactos.

Base exata: `2ad629831e5ff7385687841ccb93030c0fabc4ee`. Commits recebidos: `d86d73b415992ab3c22183bdeeb5b5c3f1fc1686` e `9dd9397ca7bdafb91bf3f18361f9c2f74f3ee1ea`. O pacote congelado E5a e os relatórios recebidos não foram reescritos. Esta página e [integration-verification.json](integration-verification.json) registram a revisão posterior.

## Resultado da revisão

A errata E5a está resolvida no adapter: identidade, join e conflitos são verificados no conjunto bruto; linhas fora de passe/corrida com times ausentes são excluídas/auditadas por jogo; candidatos continuam exigindo participantes válidos antes dos filtros. As contagens de manifesto usam linhas brutas únicas, não a população filtrada.

As somas conservam coeficientes/expoentes decimais sem arredondamento intermediário dependente do contexto Decimal. EPA finito tem seu denominador próprio; ausência/não finito não elimina volume. Geral reconcilia passe/corrida e ataque reconcilia defesa adversária, sem inversão. Foram lidos os módulos e testes de inputs, validation, population, statistics, provenance, artifact e CLI.

Proveniência explícita é uma declaração do chamador ligada aos hashes, não autenticação externa da evidência. UNKNOWN permanece UNKNOWN; contagens de subset não viram volume certificado. Fonte completa vazia exige declaração/evidência e contagem explícitas. O calendário conserva jogos sem observação de fonte.

## Verificação reproduzida

- Suite ETL offline: **162 testes aprovados**, incluindo 83 novos. Executada sobre o código da worktree recebida, com PYTHONPATH dessa worktree e runtime já instalado na origem, sem cache pytest ou escrita de bytecode.
- E5a: **26 exemplos, 23 testes e 12 hashes** preservados. O diagnóstico histórico de fronteira continua reproduzindo a limitação do modelo candidato; isso não é falha do adapter novo.
- CLI real na integração: duas execuções em destinos novos produziram os mesmos seis arquivos, byte a byte iguais ao resultado sintético versionado. Conferidos independentemente os cinco hashes de COMPLETED.json e calculation_id, removendo o próprio ID antes de recanonicalizar o conteúdo.
- CLI real recusou sobrescrita com código 2 e bytes preservados. Candidato com time ausente foi rejeitado com código 2, sem diretório final ou `.pending-*` remanescente.
- Sintético: 27 linhas brutas, 26 únicas, 14 elegíveis e 60 registros de estatísticas. ID: `sha256:2c364020c9c5bf08c2eeaa5fd38eae161920e482cdf23d2b1dda29b4d61a245f`.
- Auditoria opcional reexecutada somente sobre arquivos locais existentes: seis hashes anteriores reconciliados; resumo idêntico ao entregue. Conversões 126/130/5 e linhas fora da população com times nulos 2.638/2.729/297. Completude/modelo continuam UNKNOWN.
- Diff e links documentais conferidos. Java/frontend não foram reexecutados: nenhuma dessas camadas mudou.

Reprodução da suite, da CLI e da auditoria: comandos em [README.md](README.md). Na revisão usou-se `PYTHONDONTWRITEBYTECODE=1`, `python -B` e, no pytest, `-p no:cacheprovider`. Destinos operacionais ficam em diretórios temporários novos; não são dependência de checkout. O JSON de integração registra resultados selecionados, não cópias volumosas dos arquivos locais.

O writer prepara os arquivos em diretório irmão e publica por rename exclusivo macOS/Linux. Testes incluem falha de escrita e disputa por destino vazio. A revisão comprova comportamento operacional e determinismo nesses casos; não é teste de recuperação após queda de energia nem certificação das evidências fornecidas.

## Próximo passo: E5b-2

Preparar persistência e proveniência em stack local isolada, seguindo o grão por jogo/revisão e as relações propostas em [E5B.md](../../../../contracts/metrics/e5a-v1/E5B.md). Primeiro reconciliar o desenho da persistência com o artefato implementado, distinguindo identidade dos bytes, conteúdo normalizado, revisão de cobertura/evidência e cálculo. Não tratar os IDs como intercambiáveis.

O writer futuro deverá preservar estado/escopo do subset, contagens/somas, declarações e referências recuperáveis de fontes. Deve provar idempotência, nova revisão para correção, rollback sem conjunto parcial, fonte ausente versus completa vazia e isolamento de acesso. Completude da fonte não significa EPA/flags completos ou amostra estatisticamente suficiente.

Archive/receipts prospectivos devem registrar o que realmente foi observado; não criar disponibilidade histórica a partir de data do jogo ou horário de execução. A normalização de timestamps recebidos neste adapter não implementa a garantia de corte/precisão ou seleção entre revisões da E5b-3. Preservar os envelopes originais/evidências necessários para essa etapa.

E5b-2 não inclui banco remoto, backfill, pipeline principal, Java, visual ou publicação. Compreensão humana E4, BASIC/FULL, as cinco falhas legadas e evolução pública permanecem pendentes. A entrega aceita calcula dados do conteúdo presente; ainda não enriquece as análises exibidas ao usuário.

Sem leitura de .env, aquisição, geração externa, alterações em banco ou instalação de dependências/modelos. Sem push, deploy ou merge em main.
