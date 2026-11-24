# Entrega situacional W1–2 · candidata ao aceite humano

Implementado e disponível em **http://127.0.0.1:18098/**: fonte preservada → cálculo offline auditável → pacote privado versionado/pinado → HTTP local validado → interface dinâmica. As três opções Resumo / Terceiras descidas / Red zone atualizam a página do confronto sem confirmação intermediária. Time, perspectiva, jogo/agregado, busca, URL, reload e histórico foram exercitados.

## Base e isolamento

Worktree gerenciada `broadcast-situational-w12-v1`, branch `codex/broadcast-situational-w12-v1`, a partir do commit exato `3f4335691c9d4d126561ed03df4b775640cae7ed`. Referência conferida limpa e no mesmo HEAD ao final. Plano commitado em `e9a4203` antes de editar a implementação; definições commitadas em `f362bdf` antes do cálculo final.

A experiência anterior foi reproduzida no navegador na instância própria antes das alterações: NYJ ataque/passe W1, 24 jogadas, EPA +0,406 e 12/24 com EPA positivo. O servidor 18097 da referência não respondia naquele momento. Nenhum processo anterior foi encerrado. Somente a instância própria inicial foi reiniciada para carregar sua nova configuração.

Fontes preservadas e backup conferidos arquivo a arquivo (162 arquivos cada), readers operacionais rederivando a materialização/input e leitura integral do bundle antigo de 588 observações. Todos os pins informados pelo usuário concordaram. SHA-256 do PBP: `4e3707397912babcd0d7d02abd3be95db8e66785250e62bf9d874f37229d895e`. Nenhuma aquisição, temporada alternativa ou substituição de semana.

[Prova de isolamento](checks/isolation.json): todos os arquivos históricos fora dos caminhos exatos autorizados permanecem byte a byte iguais. Snapshots públicos, contratos anteriores, banco/migrations, Supabase, Gemini, ETL semanal, publicação e gates históricos preservados. Não houve merge, push, deploy ou publicação. O build público mantém os mesmos hashes:

- JS `73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5`.
- CSS `2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d`.

## Resultados e reconciliação

O auditor independente lê o Parquet bruto com outro algoritmo, máscaras de colunas e reconstrução de eventos terminais. Não importa o projetor nem usa suas funções de elegibilidade/acumulação como oráculo. Compara integralmente os ledgers, os 192 documentos e 384 medidas, inclusive cada adversário, unidade, exclusão, denominador, desfecho e união W1–2; enumera independentemente a matriz esperada. [Script](reconcile.py) · [Resultado integral](reconciliation.json) · [Censo dos campos](field-audit.json).

| Amostra de ataques, sem duplicar a visão defensiva | Tentativas de terceira | Conversões | Campanhas red zone | TD ofensivos dessas campanhas |
| --- | ---: | ---: | ---: | ---: |
| W1 | 377 | 154 | 108 | 70 |
| W2 | 410 | 169 | 100 | 54 |
| União W1–2 | 787 | 323 | 208 | 124 |

São totais de auditoria da amostra, sem comparação qualificada entre times. A fonte contém 5.489 registros, 32 jogos e 32 times. Nenhum agregado usa média de taxas ou soma de documentos sobrepostos.

Nas terceiras há 882 candidatos down=3: 592 pass, 200 run, 75 no_play, 13 ajoelhadas e dois field goals. A população do projeto exclui 75 no_play, 13 ajoelhadas, cinco abortadas e dois field goals: 787 incluídos. Não há spike, duplicata game/play, distância ausente nem flag positiva de terceira fora de down=3 na amostra. As flags de conversão/falha dos incluídos são complementares. As exclusões são decisões explícitas do projeto; não se afirma reproduzir uma taxa oficial da NFL.

`first_down_penalty` não é sinônimo de `third_down_converted`. No_play com avanço por penalidade fica fora; flag de falha com first down por falta pode coexistir em jogada mantida. Dois scrambles anulados conservam qb_scramble=1 na fonte, mas play_type=no_play; foram excluídos, demonstrando por que classificar apenas por flags aéreas/terrestres seria incorreto. Sacks pertencem a pass e scrambles mantidos a run, sem chamar isso de passes lançados/dropbacks. Faixas do projeto: 1–3, 4–6 e 7+ jardas.

Foram reconciliados 684 blocos fixed_drive em sequência order_sequence, sem campanha reaberta ou posse ofensiva conflitante. Os casos em que drive diverge de fixed_drive foram registrados por jogo. 208 campanhas alcançam posição pré-evento de até 20 jardas inclusive; 124 terminam em TD ofensivo. As restantes têm desfechos demonstrados pelos eventos; 472 campanhas não têm entrada e dois blocos não têm scrimmage atribuível. Tentativas após TD não criam entrada, e TD marcado de fora não cria oportunidade artificial.

As seis diferenças com drive_inside20 são todas entradas estabelecidas exatamente na linha de 20: NYG W1 campanha 14 (kneel); MIN W1 campanha 5 (passe/FG); GB W1 campanha 6 (penalidade no_play); BUF W2 campanha 18 (kneel); LA W2 campanha 21 (kneel); WAS W2 campanha 15 (TD de 20 jardas). O projeto inclui a linha; o campo auxiliar não foi usado como resposta pronta. O ledger conserva os IDs de cada evento. `drive_ended_with_score` também não é usado como TD: pode haver FG.

A primeira geração expôs dois tratamentos de desfecho incorretos fora da red zone: punt com muff recuperado por quem chutou e safety em penalidade no_play. O projetor foi corrigido para priorizar o evento correto; outra geração foi criada sem sobrescrever a primeira. O pacote final reconciliado tem zero divergências e nenhum documento insuficiente nos registros reais. Existem cinco recortes red zone sem oportunidades (ATL W1/W2/W1–2, PIT defesa W1 e CAR defesa W2); não recebem 0%.

## Artefato e cadeia operacional

Pacote final e cópia física verificada estão em Downloads, fora das worktrees; caminhos completos, pin e comandos em [README](README.md). O pin ativo é `sha256:2af2a33211c09658fb6b831188dc5c5ac3bee9b3fc4b2b6008748921ac7c339c`. O reader recalcula todos os documentos/ledger usando o Parquet contido no próprio pacote. A cópia passou no reader em processo novo, com acesso ao principal, às recuperações e ao bundle antigo bloqueado. Não há fallback automático.

O endpoint privado serve snapshot congelado após validação no startup. [HTTP](checks/http.json): resposta integral comparada ao reader, 192 documentos idênticos e sete recusas de método/Host/Origin/marcador/corpo/query/subcaminho. O transporte anterior não mudou; os 588 documentos antigos e dez recusas foram reconferidos na nova porta. [Prova anterior](checks/legacy-http.json).

A renderização real de todos os 384 contextos foi confrontada com os arredondamentos HALF_UP calculados independentemente. Time, perspectiva, jogos, razão e texto de contexto também foram verificados. O teste privado real só roda com caminho de QA explícito; esteve habilitado nesta entrega. Fixtures sintéticas são exclusivas dos testes.

## Interface e inspeção

Mantidos Archivo/Roboto Condensed, ardósia, painéis editoriais claros, cores dos times, transições e marcas transparentes/brancas. Sem aquisição de imagens, placas claras nas logos ou retratos de jogadores nas estatísticas de times. Fundamento aparece somente no resumo; tipo de análise é um controle separado. As terceiras têm barras proporcionais de conversões/tentativas por distância, escala e razões; red zone usa uma marca por campanha e desfechos, com equivalente textual/ARIA. Os fatos descrevem o recorte numericamente, sem prognóstico ou causalidade.

O navegador integrado confirmou NYJ W1, defesa agregada W1–2, MIN W2 desde a busca, ATL com zero oportunidades e BAL W3 sem fonte; troca de participante, famílias/lado/período, URL inválida, reload, voltar/avançar, retorno à busca, teclado/foco e metodologia. Cinco trocas rápidas geraram zero requisições novas, usando o snapshot já validado em memória. Não houve seleção dependente de resposta atrasada.

Capturas em 1440, 390 e 320 e fonte raiz 200% foram inspecionadas. Foram corrigidas a legenda das barras que precisava quebrar linha e a quebra do quadro de desfechos com texto ampliado. Na rodada refinada, os elementos situacionais não apresentaram overflow interno nem a página overflow horizontal. Viewport/fonte temporários foram restaurados. [Registro](evidence/browser.json). As capturas de iteração permanecem como diagnóstico; os links de resultado em README usam final/refined quando aplicável. Não se afirma teste em dispositivo físico ou estudo de compreensão humana.

## Checks e limitações

- 582 testes Python passaram, incluindo 34 casos sintéticos situacionais: penalidades, first down por falta, sack/scramble, kneel/spike, abortadas/deletadas/duplicadas, distâncias, reentrada, TD de fora, turnover/FG/fim de período, flags ausentes/contraditórias e campanha incompleta.
- 255 testes frontend passaram em 26 arquivos, incluindo todos os 384 contextos reais; cinco expected-failure legados preservados sem alteração.
- Lint, journey:build, real:build, experience:build, build público, readers, cópia independente, reconciliação, dois transportes e isolamento passaram. [Logs](checks/).
- A fronteira Node foi ajustada ao padrão mjs já existente após o compilador apontar ausência de tipos Node no novo adaptador TS. Não foram adicionadas dependências, excluídos caminhos do compilador nem relaxadas verificações.

Completude, cobertura esperada, identificação do modelo EPA e conhecimento temporal permanecem UNKNOWN. A região inclui a linha de 20 por decisão documentada; a oportunidade exige posição estabelecida observada. As terceiras excluem ajoelhadas/spikes/abortadas por definição do projeto. Esses recortes descritivos não são ranking, capacidade comprovada, previsão, estatística individual de quarterback nem garantia de representar todos os eventos esperados. As demais semanas continuam no calendário, com fonte situacional ausente nesta entrega.

Servidor próprio conferido **PID 49375**, `node scripts/journey-dev.mjs`, somente **127.0.0.1:18098**, strictPort. Inicialização e encerramento direcionado em README. HEAD exato e estado final da árvore são entregues no chat para evitar hash autorreferente neste relatório. Aceite técnico concluído; **aceite humano das análises e apresentação pendente**.
