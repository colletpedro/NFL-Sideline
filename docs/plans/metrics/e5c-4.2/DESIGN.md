# Plano visual antes da implementação

Base limpa 5bf78873cce0d1711c44f187744702af0b377aa4. As 12 referências integrais foram vistas; 02/04 orientam painel e alinhamento, 01/03/05 as faixas, 06–12 profundidade e ancoragem de marca. Não copiamos conteúdo nem recortes das imagens.

Direção: uma placa ampla de transmissão sobre cenário carvão, cabeçalho do time (nome à esquerda, logo à direita), contexto ardósia, controles compactos neutros, corpo claro com gráfico de composição à esquerda e EPA/amostra à direita, limite legível no rodapé. Mobile reorganiza a estatística em linhas, sem comprimir a faixa de TV.

```
[Baltimore / RAVENS                           logo]
[Ataque / Passe + corrida        período histórico]
[ataque/defesa] [fundamentos]       [Alterar recorte]
[56,5% | 65 de 115 jogadas       ] [EPA +0,223     ]
[parte positiva | zero/negativo ] [amostra / jogos]
[modelo EPA não identificado + dependência do SR ]
[limites da leitura                              ]
[volume por jogo / precisão / origem expansíveis ]
```

Primitivos: carvão #171C20; painel #E3E8ED → #CED6DF; tinta #18252D; contexto #3A4853; dados #32677D / #ACB9C4. Ação escura sobre claro; lima fica na marca e foco. Temas independentes do helper público.

Prova A Barlow/B. Semi/B. Condensed e B IBM Plex Sans/Condensed criada em /broadcast/type-proof.html. Barlow escolhida provisoriamente após inspeção: nome condensado real deixa respiro ao logo, corpo e números têm parentesco e maior economia de largura. Plex é legível e mais larga, com tom técnico. Não afirmamos identificar fontes ESPN. Sem scaleX e sem dependência de Impact/Georgia no piloto.

Gráfico: pergunta “quantas jogadas com EPA foram positivas?”; values.successRate e totals.successN/epaN; complemento epaN-successN via BigInt. Total único, rótulos e textura distinguem partes; alternativa textual inclui contagens e taxa. Nenhuma célula/ponto representa jogada. EPA permanece número assinado, sem escala inventada. Fonte ausente e base zero suprimem a geometria.

Consulta UI/UX Pro Max retornou hero promocional vermelho e Bebas: não aplicada por contrariar o briefing. Aplicados critérios de contraste, alvos 44px, foco, texto acessível e reflow. Tokens seguem primitive → semantic → component da skill design-system, em escopo local.
