# Relatório · entrega 4/5

**Fluxo concluído para os 32 confrontos W1–2.** Cada URL abre o próprio jogo, duas produções, dados/limitações e evidências. A coleção é nova, privada, pinada, integralmente validada e recuperável fora da worktree. Sem implementação antecipada da 5/5 e sem nova sessão humana.

## Resultado e identidade

Base limpa conferida na branch/HEAD exatos do pedido; worktree gerenciada nova e branch `codex/broadcast-matchup-w12-v1`. Plano e inventário anteriores à implementação em `28cab5e`. Coleção/reconciliação em `1e830a4`; interface/transporte em `54c10cf`; texto do estado EPA individual refinado em commit posterior, seguido pelo fechamento documental. HEAD e árvore final são verificáveis por Git e informados no chat.

Pin operacional: `sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc`. 50 arquivos físicos por árvore final, incluindo 32 documentos, índice, política/definições e cópias completas das fontes. Cópia e reprodução em processo novo com origens e worktrees históricas bloqueadas passaram; os caminhos históricos são procedência, não dependências. A fonte operacional permanece explícita, sem recuperação automática.

## Reconciliação integral

O auditor novo não importa o projetor/política novos. Reutiliza o auditor independente situacional para 882 candidatos/684 campanhas e aplica máscaras/agrupamentos próprios aos brutos, fontes EPA originais e calendários embutidos. Confere os 32 trios de placar e participantes/período, 64 produções, 192 EPA/somas/denominadores/ausentes/não finitos/precisão, cruzamento real distância × tipo, entrada/terminal de cada campanha, permissões/fatos e os inventários semanais.

**Sem divergências:** 787 tentativas elegíveis (323 conversões), 208 campanhas elegíveis (124 TDs). A conferência principal é por jogo/unidade, não esses totais. [Detalhes por partida e arredondamentos](checks/reconciliation.json), [auditoria situacional preservada](checks/reconciliation-situational.json), [matriz de estados](MATRIX.md).

| Semana | Terceiras | Referência com taxa | Red zone | Referência com taxa |
| --- | --- | --- | --- | --- |
| W1 | 154/377 | 32 ataques | 70/108 | 31 ataques; ATL sem oportunidades |
| W2 | 169/410 | 32 ataques | 54/100 | 31 ataques; ATL sem oportunidades |

Cada referência inventaria os 32 candidatos. Taxa conjunta vem das somas, sem média de taxas. Defesa não adiciona amostra. Participantes pertencem à referência; não há independência, ranking certificado, previsão ou referência EPA da liga.

Estados reais: todas as 192 observações EPA e as 64 terceiras disponíveis; red zone 62 AVAILABLE e dois NO_OPPORTUNITIES. Não há SOURCE_ABSENT/INSUFFICIENT reais neste inventário. Esses estados e EPA ausente num só ataque são testados por mutações sintéticas, separadas dos dados da experiência. ATL W1/W2 é 0/0 sem taxa; o adversário continua legível. 1/1 é mostrado com denominador, sem estabilidade.

## Interface, transporte e continuidade

Estrutura vertical, ardósia, Archivo/Roboto Condensed e cores/logos existentes preservados. Sem novos ativos, retratos decorativos ou seletores obrigatórios. EPA conserva controle local Geral/Passe/Corrida e o esclarecimento aprovado. Escalas comuns por recorte; zeros/sinais/denominadores próprios preservados. Unidades, regras e auditoria ficam nas profundidades do piloto.

Resumo usa somente as três famílias autorizadas; compara frações antes do arredondamento e omite família com taxa inexistente. A política tem operação editorialFact explícita; diferenças/lado a lado/referências não herdam permissão apenas porque um dado está disponível. Recusa conjunta preserva exibições individuais autorizadas. Mercado continua separado, campos existentes/valor bruto/origem; captura/fornecedor/historicidade UNKNOWN.

URL direta `/?view=matchup-w12&game=ID`; season/week opcionais são conferidos quando presentes. Erro explícito para ID desconhecido/período incompatível. Calendário reutilizado com links novos; semana/busca/filtros/página voltam ao contexto de origem. Recarga, histórico, anterior/próximo e busca W1 a partir de W2 conferidos.

Reader Python completo no startup, validação adicional de identidade/hashes no Node e cliente, bytes congelados, loopback/strictPort, inventário fechado de IDs, GET exato, Host/Origin/marcadores/corpo restritos. Fonte ausente recebe 503 sem substituição; marcador antigo 409; ID fora do inventário 404; pedido inválido 403 (Expect pode receber 417 do Node). [59 requisições, todos os 32 documentos exatos](checks/http.json). Uma segunda inicialização recusou a porta ocupada; nenhum processo foi encerrado para liberá-la.

O último acabamento renomeou metadados temporais herdados do piloto, sem mudar valores/unidades/fatos/permissões. `temporalContext.otherGamesContextAllowed=false` restringe composição de contexto temporal de outros jogos, não a referência transversal da mesma semana, que tem `referenceWeeks` explícito. [Igualdade de todos os outros campos nos 32 jogos](checks/visible-data-preserved.json). Todos os checks finais de identidade/HTTP/matriz usam o pin final.

## Verificações realmente executadas

- **626 testes Python completos**, habilitando os bundles reais; depois dos últimos acabamentos, **18 pertinentes novamente**, incluindo rederivação integral, recuperação, recusa de sobrescrita/symlinks/diretórios extras/destinos sobrepostos e adulteração mesmo após recalcular hashes externos.
- **302 frontend completos**, repetidos com o pacote final; cinco `it.fails` legados preservados. Casos: 32 documentos/192 EPA contra oráculo decimal independente, estados separados, 0/0 sem taxa, comparação recusada com dado individual, EPA ausente de um ataque, identidade/URL/byte hash incompatíveis e cruzamentos reais. Python confere empate exato e taxas diferentes que arredondam igual.
- Lint sem warnings, TypeScript journey/matchup/W12, seis builds (journey, matchup, W12, real, experience, público). Lint/TypeScript e W12 repetidos após os acabamentos. A entrada HTML experimental usa `order:pre` para ser compilada tanto em desenvolvimento quanto no build; o gate lê o JavaScript gerado e exige endpoint, contrato e pin W12 no build privado, ausentes do público. [Recibo do build final](checks/final-build-receipt.json). [Logs e comandos](checks/builds.json), [frontend final](checks/frontend-final.log), [Python final pertinente](checks/python-final-targeted.log).
- Build público normal e sob `VITE_*` hostis idênticos aos hashes de 18103: JS `73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5`, CSS `2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d`. Arquivos públicos/cliente/seleção por build/snapshots/backend/schema/ETL de publicação intactos.
- Navegador: **32 jogos finais**, títulos/participantes/placares, 64 EPA gerais contra oráculo independente, 787 marcas de terceira e 208 campanhas vinculadas ao ID correto, referência W1/W2 própria; nenhuma mistura ou overflow. [Recibo](evidence/browser-all-games-final.json).
- Matriz representativa: **quatro jogos × três larguras = 12 casos** em 1440/390/320. NYJ/TEN 1/1, ATL/PIT e CAR/ATL sem oportunidades, JAX/DEN com nomes longos. Capturas finais completas e inspeção de blocos representativos; checagens DOM sem cortes/rolagem horizontal e logos carregados. [Matriz](evidence/visual-final.json). As capturas de blocos durante o acabamento têm os mesmos dados visíveis; as 12 capturas finais pertencem ao pin final.
- Geral/Passe/Corrida em três larguras: **nove combinações** conferidas no navegador, mesma escala nos dois ataques. Tab/Enter, foco visível, regra EPA e marcas de terceira/campanha/referência consultadas. Texto a 200% em 320 px, corpo 32px, sem overflow/corte; fonte restaurada. [EPA](evidence/epa-browser.json), [teclado/200%](evidence/accessibility.json).
- Falha real de requisição no browser, sem números de outro jogo, seguida de recuperação da mesma fonte. URL desconhecida e incompatibilidades explícitas. Resposta real de IND/KC retida por wrapper temporário de fetch que ignorava AbortSignal somente no teste, liberada após JAX/DEN: a página permaneceu JAX/DEN, sem marcas antigas. Wrapper/interceptação/rede/fonte temporários foram restaurados. [Falha](evidence/source-failure.json), [URLs](evidence/invalid-urls.json), [ordem invertida](evidence/out-of-order.json), [calendário/histórico](evidence/calendar-flow.json).

Não se contam cliques/capturas do agente como pessoas. Não houve nova avaliação humana ou reconfirmação do esclarecimento de EPA. N=1 anterior não demonstra usabilidade ampla. Completude, cobertura esperada, identificação do modelo EPA e conhecimento pré-kickoff continuam UNKNOWN. Não foram executados Java/banco porque não houve mudança correspondente; nenhuma credencial foi carregada.

## Isolamento e passagem

Seis listeners anteriores preservados: 18098/30244, 18099/30251, 18100/30265, 18101/95101, 18102/97976 e 18103/44780. Referência 18103 permanece limpa no HEAD original; respostas antigas iguais ao artefato do piloto. O servidor próprio inicial foi trocado apenas por sua instância durável; operação e encerramento direcionado no README. [Isolamento](checks/isolation.json).

A 5/5 recebe uma coleção nominal/reproduzível e página de confronto concluídas. Página de time, agregados e reorganização do hub semanal continuam fora desta entrega. Sem merge, push, deploy ou publicação pública.
