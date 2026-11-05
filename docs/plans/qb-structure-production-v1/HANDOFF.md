# Passagem — revisão antes de integrar

Pesquisa concluída em worktree gerenciada isolada, branch `codex/qb-structure-production-v1`, derivada exatamente de `01f23cfc64fee10f5b16dafae7eb4dabeff8579c`. Contrato inicial `9b5fecb`, implementação `c8b1c97`; os commits seguintes registram testes de revisão e resultados. O commit que contém esta passagem é a entrega documental; consultar `git log` para o HEAD completo, sem tentar embutir o próprio hash no conteúdo versionado.

A base `codex/qb-risk-outcomes-lab-v1` permanece no HEAD informado, limpa, com arquivos rastreados e stores M3/B2 byte a byte preservados. A referência [18125](http://127.0.0.1:18125/?view=risk-lab&season=2026) não respondeu antes nem depois desta sessão; a checagem final confirmou conexão recusada e nenhum listener na porta. Nenhum processo foi iniciado, encerrado ou reconfigurado. A preservação dos arquivos/stores está comprovada; a disponibilidade da prévia não foi demonstrada. O principal conserva suas alterações preexistentes. [Resumo de preservação](evidence/preservation-summary.json). Sem merge, push, deploy, publicação, credenciais, Gemini, retreino, banco ou ETL operacional.

## Resultado que merece revisão

A métrica operacional é consistente e auditável, mas a comparação é sensível à definição. Em 2026, liga QB: A=0,230 EPA/jogada (6.340); B=0,309 (909); S1 B=0,009 (1.264); S2 B=−0,519 (1.820); S3 B=0,163 (475). Em 10/15 jogadores da coorte principal o sinal muda com S2. A frequência se mostrou historicamente mais estável que a diferença de EPA. Não traduzir isso em dependência do sistema ou habilidade individual persistente.

Há 8.962 dropbacks em 121 jogos de 2026, W1–8; todos com FTN e EPA. Principal histórico: 69.505 em 2023–2026. 2022 é auditoria separada. O residual atual é 799, principalmente 797 DES, além de aborto e scramble WR; não é sinônimo de falta de cobertura. Scrambles são identificados por PBP e rusher auditado, sem depender da instabilidade histórica da flag SD nas corridas.

Exemplos determinísticos completos no [relatório](REPORT.md): Mahomes (A alto, B próximo de zero), Maye (B alto), Willis (diferença próxima de zero), Stroud (sensível à definição ampliada) e Stafford (sete B, pouco suporte). Cada caso entrega todas as jogadas, contribuições, contexto, regras e descrições. Nenhuma intenção ou culpa é inferida da descrição.

## Contrato do pacote candidato de consumo

Store: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-structure-production-v1/20261105-v1`.
Entrada única candidata: `package-release/index.json` (schema 1, métrica/classificação 1.0.0). Validar `manifest.json` e hashes de fontes/código/contrato; não escolher por data/nome de diretório nem buscar a saída intermediária mais recente. **Não há ponteiro ativo criado.**

| Arquivo | Contrato e uso posterior |
| --- | --- |
| `index.json` | versão, períodos principais, status experimental, 199 GSIS, referências de arquivos, limites e atribuição |
| `sources.json` / `fixed.json` | manifest da fonte e hashes fixos de regras/agregação/contrato; fonte física indicada no índice |
| `coverage.json` | jogos incluídos, futuros e pendências de encerramento por temporada; 2026 não depende de semana completa |
| `classification-contract.md` | universo, regras e esclarecimento sobre identidade conhecida de rusher não-QB |
| `plays.parquet` | 89.715 linhas elementares, incluindo 2022 para auditoria; consumir **somente season≥2023** nas comparações principais |
| `audit/plays_2022.parquet` | auditoria separada; jamais misturar à comparação principal por omissão de filtro |
| `categories.csv` | seis categorias por GSIS/temporada, inclusive vazias, n/n_epa/soma/média/jogos/composição |
| `comparisons.csv` | A/B, diferença com sinal A−B, main/S1/S2/S3, frequências, volumes e suporte; A fixo |
| `league.csv` | QB auditados, ponderação por jogadas, separado por ano/categoria; inclui pouco suporte individual |
| `players/{gsis}.json` | categorias, quatro comparações e todas as jogadas principais do jogador, incluindo originais e contexto |
| `context_*.csv` | distribuição/média/mediana pré-jogada de A/B por temporada, faltantes explícitos |
| `extreme_diagnostics.csv`, `group_extremes.csv`, `extreme_plays.parquet` | diagnóstico de concentração/influência, sem corrigir a métrica principal |
| `stability.csv` | pares de anos, suporte comparável e correlação descritiva, sem prova de habilidade |
| `examples/` | seleção por critério, todas as jogadas e extremos para localizar contribuições |
| `figures/` | cinco PNG/SVG científicos e CSVs de suporte |
| `revision.json` | inicial ou diferenças por chave/campo em atualização; antes/depois e manifest anterior |

Campos `player_id` são GSIS. `position_class` separa `qb`, `other`, `unknown_or_conflicting`; nomes são exibição, nunca chave. Contagens são eventos e médias são EPA/jogada. `n_epa` pode ser menor que n. Nulos significam indisponibilidade, não zero. `unavailable_no_opportunities` e `unavailable_epa` não podem ser plotados em zero. `low_support` conserva o valor e exige marca visível. `legible` é só corte de volume.

`pct_all` usa todos os dropbacks; `pct_classifiable` exclui o residual inteiro, inclusive DES. Não trocar entre eles sem rótulo. O percentual B principal usa todos os dropbacks. Residual sempre deve ser decomposto por motivo. Outras posições continuam consultáveis sem entrar nas médias de liga QB.

O detalhe contém `rule`, `reason`, `event_type`, `read_thrown`, `read_normalized`, flags originais, `charting_present`, `identity_source`, `identity_status`, EPA/contexto e descrição da fonte. Não expor um código de leitura em sack/corrida como se fosse passe lançado naquela leitura.

## Próxima apresentação recomendada

Após revisão humana dos resultados, integrar em outra entrega uma leitura experimental com X=EPA/jogada em improvisação identificada e Y=EPA/jogada em progressão registrada; referências de liga condicionais, identidade, suporte e frequência juntos. Mostrar as seis categorias e residual conhecido DES. Toggle explícito principal/S1/S2/S3, conservando volumes e status; detalhe deve decompor SD/scramble/throwaway/sack, não apenas mostrar diferença.

Usar denominação estrita do observado; evitar ranking de “sistema”, quadrantes de qualidade ou promessas de causalidade. Mostrar contexto e influência de extremos como diagnóstico, mantendo todos os EPA no resultado. Não misturar expectativas M3/B2 com esta métrica descritiva, nem alterar suas fontes/ponteiros. As figuras desta pesquisa não redesenham a experiência visual do laboratório aprovado.

## Validação e continuidade

42 testes novos offline passaram no ambiente novo, incluindo atualização com fonte sintética revisada e preservação da versão anterior. Regressões legadas em processos separados: M3 23, B2 33, pacote do laboratório 6. Reconciliação independente SQLite a partir dos brutos: todas as chaves/categorias/identidades/EPA, contagens exatas e 1.643 agregados não vazios de 2023–2026; também 2022 separado. Verificador reconstrói todas as sensibilidades e denominadores.

Reprodução de fontes recuperadas em destino novo e ambiente instalado offline: 256/257 arquivos idênticos; só localização absoluta da fonte no índice difere. O manifest muda em consequência; equivalência numérica a 1e−12 e linhas/figuras exatas são registradas separadamente. Replay da atualização com fonte congelada: zero chaves/campos alterados; pacote anterior preservado. [Reprodução](README.md).

A aquisição com rede não foi repetida porque as fontes autorizadas já estavam congeladas. O comando de atualização está implementado, verifica regras fixas antes da aquisição e registra uma revisão própria, sem ativar nada. Suporta 2026; outro ano exige revisão de contrato de fonte. O arquivo final de recuperação inclui fontes, pacote, código, documentos e wheels, com extração/hashes verificados localmente, sem alegação de backup remoto.
