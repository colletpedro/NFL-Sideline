# SIM01 — ensaio fictício solicitado pelo usuário

Data: 24/10/2026, America/Fortaleza. **Simulação por IA; nenhuma pessoa participou.** Todas as falas abaixo foram inventadas para ensaiar o roteiro. O agente já conhecia a página e o gabarito; não houve primeira exposição independente. Ações descritas como verificadas foram executadas pelo agente no navegador. Reações, dúvidas e classificações do personagem são hipotéticas.

O ensaio não entra nas fichas P01–P05, no N humano, nos limiares 4/4 ou 4/5 ou em incidências de problemas. Não foram atribuídos consentimento real, tempo de execução humano ou resultados observados a uma pessoa inexistente.

## Perfil fictício

- NFL: acompanha jogos semanalmente e melhores momentos.
- EPA: já ouviu, mas não usa.
- Outras estatísticas avançadas: familiaridade básica.
- Página: primeira visita no cenário fictício; o agente já a conhecia.
- Ambiente realmente usado pelo agente: navegador integrado no computador hospedeiro, painel de 532 × 827 px, automação de cliques. Sem teste humano de mouse, teclado ou toque físico.
- Página: http://127.0.0.1:18102/?view=matchup-reading.
- Preparação executada: recarga, Geral selecionado e detalhes inicialmente recolhidos. Interface preservada.

## T1 — Terceiras

Enunciado: “Compare o que os dois ataques fizeram nas terceiras descidas. O que você conclui e onde encontrou essa informação?”

**Fala fictícia:** “TEN converteu mais: quatro de doze, 33,3%. NYJ fez duas de dez, 20%. Então TEN teve maior aproveitamento nesse jogo. Vi primeiro no resumo e conferi em Terceiras.”

- Caminho verificado: clique em “Ver terceiras: NYJ 2/10; TEN 4/12”, saindo do resumo para o bloco de terceiras.
- Evidência realmente exibida: dois ataques, razões 2/10 e 4/12, taxas 20,0% e 33,3%, faixas de distância e legenda de formas/preenchimento.
- Dificuldade fictícia: nenhuma para a comparação geral. Entendimento das marcas individuais não demonstrado pela fala; não inferir compreensão da legenda só porque está disponível.
- Exploração de distâncias pelo personagem: não observada; não inventar descoberta espontânea de 1/5.
- Ajuda roteirizada: nenhuma.
- Classificação da resposta inventada: correta para a comparação geral; não constitui acerto humano.

## T2 — Período

Enunciado: “De qual jogo ou período são esses números? O que na página indica isso?”

**Fala fictícia:** “É Jets contra Titans, semana 1 de 2026. Lá em cima tem o resultado e a data, e os blocos dizem ‘deste jogo’.”

- Evidência verificada: cabeçalho NYJ × TEN, resultado 23 × 10, 13 de setembro de 2026, 2026 REG, Semana 1, e “Leitura retrospectiva deste jogo”.
- Caminho técnico: leitura do cabeçalho e dos textos no DOM. Não foi observado um usuário rolando de volta ao topo; esse caminho humano permanece hipotético.
- Ajuda roteirizada: nenhuma.
- Classificação da resposta inventada: correta. Não há evidência humana sobre a eficácia das pistas.

## T3 — Red zone

Enunciado inicial: “Compare os dois ataques na red zone e explique sua conclusão.”

**Fala fictícia espontânea:** “NYJ fez dois touchdowns e TEN um. Mas TEN aproveitou 100% e NYJ 66,7%. São duas comparações diferentes.”

Complemento, mantido após o espontâneo: “Quem teve maior taxa? Quem marcou mais touchdowns? O que o 100% de TEN permite concluir?”

**Fala fictícia após complemento:** “TEN teve a maior taxa e NYJ mais touchdowns. O 100% foi um TD em uma campanha; não dá para concluir que TEN vai ser sempre melhor nisso.”

- Caminho verificado: atalho “Red zone”.
- Evidência exibida: NYJ 2/3 e 66,7%, com marcas TD/FG/TD; TEN 1/1 e 100,0%, com uma marca TD; explicação de uma marca por campanha e limite de uma oportunidade.
- Unidade na resposta fictícia após complemento: campanha.
- Ajuda adicional roteirizada: nenhuma. O complemento é parte padronizada da tarefa.
- Classificação inventada: distinção taxa/contagem correta no espontâneo; limite da amostra explicitado após complemento. O limite não deve ser registrado como percepção espontânea neste cenário.
- O resumo inicial também entrega parte da comparação. Uma futura resposta humana correta pode vir dele; isso não demonstra que a pessoa compreendeu as marcas do gráfico.

## T4 — EPA

Enunciado inicial: “Compare a produção dos dois ataques pelo EPA. Explique, com suas palavras, o que os valores mostram.”

**Fala fictícia espontânea:** “NYJ está positivo, +0,168, e TEN negativo, −0,119. Parece que NYJ produziu mais. Vejo 60 e 49 jogadas, mas não sei explicar exatamente o que esse valor de EPA mede.”

Pedido posterior: “Agora consulte somente o passe e compare os dois ataques.”

**Fala fictícia após pedido:** “Tem Passe ao lado de Geral. Agora NYJ está +0,406 em 24 jogadas e TEN −0,210 em 35. NYJ continua acima, mas ainda não sei explicar direito a unidade.”

- Caminho verificado: atalho “EPA”, depois botão “Passe”.
- Evidência exibida antes: +0,168/60 e −0,119/49, com título “pontos esperados por jogada com EPA válido”. Depois: +0,406/24 e −0,210/35; os dois ataques continuam presentes e o texto informa que passe inclui sacks.
- Classificação inventada: interpretação conceitual parcial; navegação do personagem bem-sucedida no roteiro. Conhecer os sinais e ler denominadores não demonstra entender pontos esperados por jogada.
- Ajuda/explicação conceitual roteirizada: nenhuma. A dúvida fictícia fica preservada até o encerramento.
- Ocorrência técnica real: o primeiro seletor da automação procurou checkbox porque a árvore nativa assim representou Passe. O DOM o expõe como botão; usando esse papel, o clique funcionou. Isso é uma divergência entre representações da automação e **não** uma dificuldade observada de participante.

## T5 — Liga

Enunciado: “Como você usaria esta distribuição para contextualizar NYJ e TEN? O que ela permite dizer?”

**Fala fictícia:** “Escolhi terceiras. Cada ponto é o ataque de um time na semana 1. NYJ está em 20% e TEN em 33,3%. Usaria para comparar o aproveitamento observado naquela semana, sem dizer que quem está à direita é necessariamente melhor ou que vai ganhar o próximo jogo.”

- Caminho verificado: atalho “Terceiras”, abertura de “Consultar os 32 pontos e seus denominadores”, seleção de NYJ pela lista.
- Evidência exibida: referência 2026 REG/W1, 32 times, legenda de um ponto por time, razões NYJ 2/10 e TEN 4/12. Selecionar NYJ na lista também selecionou o ponto correspondente.
- Limite do percurso: o agente não testou descoberta visual independente de NYJ/TEN nos pontos sem usar a lista. Não concluir que esse problema está resolvido.
- Ajuda roteirizada: nenhuma.
- Classificação inventada: correta no cenário. Não fornece incidência real nem evidência de descoberta espontânea.

## T6 — Conferência

Enunciado: “Se quisesse conferir como um desses números foi calculado, onde procuraria?”

**Fala fictícia:** “Eu iria em Método e procedência e abriria as regras para ver o que entra na conta. Se fosse uma tentativa específica, tentaria consultar a marca.”

- Caminho verificado: atalho “Método”, abertura de “Consultar regras, exclusões e penalidades”.
- Evidência exibida: definições completas, numerador/denominador de terceiras, elegibilidade, exclusões e unidade de campanha na red zone.
- O caminho por marcas individuais foi apenas mencionado pelo personagem; não foi executado nesta tarefa do ensaio.
- Ajuda roteirizada: nenhuma.
- Classificação inventada: correta para encontrar um caminho pertinente; não exige domínio dos documentos completos.

## Encerramento fictício e leitura do ensaio

**Comentário fictício:** “Consigo comparar as taxas e as contagens. EPA ainda pede mais familiaridade minha.”

O ensaio demonstra caminhos funcionais executados pelo agente: atalhos, Passe, lista da liga e acesso às regras. Ele não demonstra que fãs reais os encontram sem instrução. A dúvida sobre EPA foi uma escolha do personagem, não um achado de pesquisa.

Hipóteses para observar em sessões reais: distinguir leitura do resumo de compreensão das marcas; separar desconhecimento de EPA de dificuldade de navegação; verificar descoberta dos times nos pontos sem depender da lista; verificar se o documento técnico com menções à base W1–2 confunde o recorte W1 explicitado na página. Nenhuma dessas hipóteses foi confirmada pela simulação.

Não há recomendação de alteração sustentada por comportamento humano. N humano permanece zero; limiares não calculados. Celular físico com toque permanece pendente. Ao terminar o ensaio, a página foi devolvida à URL inicial sem hash, no topo, com Geral e detalhes recolhidos; captura e estado em `evidence/` desta pasta.
