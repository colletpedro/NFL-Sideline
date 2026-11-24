# Fechamento local · entrega 5/5

Percurso integrado para os **32 jogos e 32 times de 2026 REG W1–2**. O hub oferece 16 jogos por semana sem busca obrigatória; o confronto abre os dois ataques, os participantes levam ao time e os dois jogos do time permitem continuar a exploração. Retorno conserva semana e consulta. Sem publicação ou cobertura além do recorte.

## Base e implementação

Referência limpa conferida em `945368956571cfc63ec1604337245fe822a138bc`, branch `codex/broadcast-matchup-w12-v1`. Nova worktree gerenciada e branch `codex/broadcast-hub-team-w12-v1`. Plano nominal anterior à geração em `78f9327`; dados/reconciliação em `5e44297`; interface/transporte em `1202586`; fechamento documental em commit local posterior, listado por Git e no chat final.

Reutilizados calendário congelado/cliente, busca, identidade/logos, formato racional exato, gráficos/unidades/regras e páginas anteriores. Nenhum framework, biblioteca, ativo, modelo ou credencial novo. Alterações compartilhadas restritas a opções adicionais da busca, helper de sugestões, links opcionais aos participantes e texto concreto de ausência no confronto. Cache Vite exclusivo da nova instância sob `node_modules/.vite-broadcast-hub-team-w12-v1`; arquivos gerados foram retirados da varredura sem alterar regras de lint; defaults dos consumidores anteriores preservados; referência 18104 usa checkout separado e permanece limpa.

[Mapa de navegação e bloco → evidência/operação](MAP.md). [Matriz integral](MATRIX.md). Destaque é reproduzível por data/ID; apoios e compactos não alteram significado ou qualidade dos registros. O diretório de times não exige seletores. A página do time mostra produção própria e dos ataques adversários nos mesmos dois jogos, sem confirmação independente ou nota geral.

## Projeção e reconciliação

Contrato/política próprios, pin novo `sha256:8971d767b6ec0557465aeb65aeb00533fd10255a62f4b916954b3854daa15cef`. 32 documentos, 64 perspectivas, 192 EPA, originais W1–2, componentes/IDs/hashes/definições/permissões. Não foi alterado o pacote da 4/5. As 787 tentativas e 208 campanhas únicas podem reaparecer na página do adversário pela perspectiva contra; não são somadas entre perspectivas nem tratadas como amostras independentes.

O auditor independente não importa o projetor ou reader novos: lê PBP bruto, ledger e originais agregados, usa Fraction para somas EPA e Decimal HALF_UP para apresentação. Confere os jogos, adversários, todos os IDs/valores, populações EPA e contagens faltantes/não finitas, coluna/hash/definição, distância recalculada do bruto, tipo/conversão/ordem, partições conjuntas, campanhas/entradas/desfechos/cronologia e agregados originais em ambas as perspectivas. **Sem divergências.** [Recibo](checks/reconciliation.json).

EPA = soma decimal exata / jogadas finitas, sem média de médias e sem filtro situacional. Terceiras e red zone = soma n/d e união real sem duplicação. Denominador nunca depende da legibilidade do gráfico. Arredondamento só na apresentação, sem converter somas para float; valor não zero menor que a precisão permanece sinalizado por limite (`+<0,001`, por exemplo). Conversão para número ocorre apenas na geometria dos gráficos.

Todos os EPA e terceiras reais estão disponíveis. Red zone tem 63 perspectivas com taxa e ATL/off sem campanhas em W1 e W2, 0/0 sem taxa; adversários contra ATL permanecem 4/8. Zero oportunidades não é ausência. Ausência/insuficiência/incompatibilidade/semana faltante/duplicação/zero+semana válida e operação recusada são casos controlados somente nos testes. Um componente ausente não é descartado para apresentar um agregado W1–2 parcial.

## Artefatos e transporte

87 arquivos físicos na raiz durável nova. Cópia física verificada com inodes distintos e reprodução a partir da recuperação, com origens históricas bloqueadas durante a prova, produziram os mesmos arquivos/hashes/pin. [Recibo da recuperação](checks/recovery.json). A coleção W12 completa está embutida, sem depender de outra worktree ou processo. Entradas secundárias usam as raízes duráveis anteriores explicitadas no README.

Reader integral anterior à disponibilização, configuração exclusiva do operador, snapshot congelado. Nova fronteira de mesma origem restrita em 18105; sem path de arquivo/seleção de fonte pelo browser. **111 requisições HTTP** confirmaram 32 documentos/índice/hashes exatos, 32 confrontos idênticos à referência e recusas de método, Origin, Host, marcador, pin, corpo, query/subpath e cabeçalhos duplicados. [HTTP](checks/http.json). Segunda instância recusou porta ocupada; nenhum listener anterior foi encerrado. [StrictPort](checks/strict-port.json).

## Verificação técnica realizada

- **132 testes Python pertinentes, sem skips**, com pacotes reais habilitados: time, coleção W12, base comparável, situacional e observações. Inclui reader integral, adulteração mesmo após recalcular hashes externos, symlink, destinos existentes e regras de agregação.
- **312 testes frontend, sem skips**. Preservados os cinco `it.fails` legados; não foram corrigidos nem removidos nesta entrega. Casos novos conferem todos os 32 documentos/192 EPA contra oráculo independente, unidades, busca/destinos, contexto, incompatibilidade, ausência/insuficiência/zero, recusa e resposta atrasada.
- Lint sem avisos; TypeScript journey e configuração própria; sete builds: hub/team, journey, matchup, W12, real, experience e público. Build público também exercitado com VITE adverso. JS público `73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5`; CSS `2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d`, ambos idênticos. Cliente público fixo e sem endpoints/pins privados.
- Gate de escopo, fontes, snapshots, arquivos históricos, referência limpa e sete listeners anteriores preservados; `git diff --check`. Sem Java/banco porque não houve alteração correspondente; sem credenciais, ETL semanal ou publicação.

[Logs e recibos](checks/), [isolamento](checks/isolation.json), [builds finais](checks/final-builds.json). Rodadas posteriores aos pequenos refinamentos ficam registradas separadamente; não se apresentam verificações antigas como checks de um código diferente.

## Navegador e refinamentos

32 identidades/logos carregados, duas perspectivas e dois jogos por time conferidos; quantidades de marcas confrontadas com os documentos reais. Matriz representativa em 1440, 390 e 320 px: hub W1/W2, NYJ, nome longo WAS e ATL sem campanhas. Nove combinações EPA (três fundamentos × três larguras) com valores/denominadores e escala comum; controle local não altera outras métricas. Teclado, foco, Escape, âncoras, regras, marcas e auditoria consultados. Texto a 200% em 320 px, fontes/viewport restaurados.

Percursos W1 → confronto → time → outro jogo → W1 e W2 → busca/time → W1 → W2 mantiveram consulta/semana; busca de partida abriu exatamente o destino escolhido. Recarga/histórico/URLs diretas e erros de identificadores/períodos conferidos. Uma resposta real de BAL foi retida, ATL abriu e continuou visível quando BAL foi liberado. Falha de requisição dos times não derrubou confrontos, e o time leu sua fonte própria mesmo com a fronteira de confrontos bloqueada. Sem fallback ou dados antigos. Wrappers/bloqueios temporários foram removidos.

A inspeção identificou e corrigiu overflow do cabeçalho, navegação de semanas, siglas dos participantes, denominadores EPA e diretório a 200%, alinhamento dos placares do destaque no mobile e uma área vazia de marcas quando ATL não tinha campanhas. Fontes não foram reduzidas. Foco foi acrescentado ao destino dos resultados de busca e o escopo existente passou a ser conservado na escolha. A síntese do time foi encurtada; a descrição da produção adversária segue perto do EPA e os limites de independência/qualidade permanecem na auditoria. Não foram redesenhados pontos da liga ou marcas do confronto. [Provas](evidence/browser.json), [matriz browser × dados](checks/browser-matrix.json), [capturas](evidence/).

## Coleta humana, interpretação e limites

**Coleta humana:** nenhuma nova sessão nesta entrega. Permanece a avaliação anterior de P01/N=1, encerrada por decisão do usuário, com paráfrases revisadas e limites documentados na 3/5. As verificações do agente não são participantes, teste de toque físico ou validação estatística.

**Interpretação:** integração e consistência técnica verificadas para este acervo. Não mede frequência de compreensão em outras pessoas. Identificação independente dos pontos no gráfico da liga, exploração humana das marcas e uso em celular físico continuam sem avaliação suficiente. O esclarecimento de EPA foi preservado, sem alegar que resolveu a dificuldade relatada.

**Refinamentos implementados:** organização solicitada do hub/time e correções técnicas de navegação/reflow descritas acima. **Reconfirmação humana:** não realizada. Não é condição nova para este fechamento.

Operações indisponíveis: referência agregada da liga, ranking/percentil, previsão/qualidade ajustada, diferença de métricas não solicitada pela política de time, completude certificada, identificação/certificação EPA e disponibilidade histórica pré-jogo. UNKNOWN continua UNKNOWN. Mercado permanece arquivado e separado somente nos confrontos. Dois jogos não demonstram tendência ou temporada completa. Nenhuma análise W3 foi criada.

## Fechamento das cinco entregas

| Entrega | Resultado local e limite |
| --- | --- |
| 1/5 | Base comparável, unidades e permissões explícitas; não certifica modelo ou completude |
| 2/5 | Leitura piloto NYJ × TEN, dois ataques juntos e rigor consultável |
| 3/5 | Uma sessão humana P01; coleta encerrada no escopo revisado; esclarecimento EPA sem reconfirmação |
| 4/5 | Coleção pinada e leitura dos 32 confrontos W1–2 |
| 5/5 | Hub semanal, 32 times e continuidade com agregados reconciliados e recuperação durável |

**5/5 encerrada como integração local de W1–2.** Sem merge, push, deploy, promoção automática ou publicação. Não é produto publicado nem validação ampla de usabilidade. Comandos, PID e encerramento direcionado estão no README; HEAD e árvore finais são informados no chat e verificáveis por Git.

Capturas representativas finais: [hub desktop](evidence/hub-1440.png), [W1/390](evidence/hub-w1-390.png), [W2/320](evidence/hub-w2-320.png), [NYJ/390](evidence/team-nyj-390.png), [WAS/390](evidence/team-was-390.png), [ATL/320](evidence/team-atl-redzone-320.png), [texto 200%](evidence/team-was-320-200.png) e [composição completa com os 32 logos](evidence/hub-directory-all.png). A referência anterior está em [18104 antes da implementação](evidence/reference-18104.jpg).
