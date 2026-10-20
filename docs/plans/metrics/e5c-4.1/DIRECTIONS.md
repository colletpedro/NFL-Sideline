# E5c-4.1 — direção antes da implementação

Continuidade: HEAD 0f8762bef1dcc0b5baaf669c797bbdc9ed7813cf, worktree limpa, branch codex/visual-reading-e5c4. E5c-4 preservada como candidata, sem aceite operacional implícito. Catálogo e COMPLETED.json conferidos com pin 2fae3be2…ace8a.

## Referências realmente inspecionadas
- https://jjettas.com/ — abertura com atleta, túnel luminoso, textura de tela e profundidade. Inspeção limitada à abertura e estrutura de conteúdo; não atribuir interações posteriores não observadas. Aproveitar camadas e atmosfera, sem vídeo/fotografia ou atraso antes dos dados.
- https://www.awwwards.com/sites/justin-jefferson — página carregada, preview com materiais/texturas, composição de painéis e identidade esportiva. Não inspecionado site inteiro por esse preview.
- https://maxibestof.one/websites/82315-nba-represent — preview desktop visível: atleta central, torcida no fundo, identidade e ações periféricas. Visualização completa exige Pro; não acessada. Usar relação foco/periferia, não copiar imagens/fontes.
- https://maxibestof.one/websites/92370-good-sport-magazine — preview visível: espaço editorial, tipografia limpa, bloco de ação lima. View completa Pro não acessada. Aproveitar separação entre ação e conteúdo.
- https://maxibestof.one/websites/sports — galeria carregada e thumbnails inspecionadas; variedade de escala tipográfica, imagens centrais e navegação discreta.
- https://alvarotrigo.com/fullPage/showcase/sports-fitness — galeria carregada, exemplos com identidade dominante. Não adotar captura de scroll/fullPage.
- https://www.awwwards.com/inspiration_search/sports/ — galeria carregada: sobreposição de imagens com tipografia grande, material de campo e contraste. Apenas thumbnails, não experiências completas.

Skills frontend-design e UI/UX Pro Max lidas. Busca de sistema sugeriu hero promocional vermelho: inadequado, descartado. Aproveitada hierarquia tipográfica condensada e contraste. Direções abaixo derivam do briefing, dos previews realmente vistos e de composição original.

## Sistema comum
Base carvão #0d1112; texto #f2f3e9; contexto #b8c6c4; ação lima #d7ff3f; dados gelo #a8dcd3; complemento grafite #354548. Gelo não significa qualidade; o lima intenso identifica seleção/ação. Erros âmbar claro. Fonte Impact/Arial Narrow para identidade de estádio e transmissão; sistema para texto/números; monospace só para anotações da prancheta. Sem ativos externos.

## A — Estádio em camadas
```
[seletor A/B/C separado]
       RAVENS (fundo gigante, iluminação/campo CSS)
[time + recorte]              [EPA / contexto]
       [65 EPA positivo | 50 zero ou negativo]
       [gráfico de área proporcional elevado]
[fundamentos e ataque/defesa em primeiro plano]
[limites] [precisão/origem]
```
A proporção é a cena, sem abertura decorativa. Bloco horizontal contínuo proporcional à população EPA, rótulos externos. Fundo decorativo não é tracking.

## B — Transmissão esportiva
```
[faixa time / temporada / fonte histórica]
[controles] | [sucesso: 65 =====   ] | [EPA]
[verticais]| [demais: 50 ====    ] | [amostra]
           [denominador comum 115]
[faixa contextual e inspeção]
```
Mais densa e operacional: rail de controles, gráfico em duas faixas de contagem com escala declarada, números no canto. Não é placar e não inventa adversário.

## C — Prancheta tática
```
[identidade compacta]          [anotação de sucesso]
[fundamentos horizontais]
[campo esquemático decorativo / gráfico por jogo]
[W1 contagem ===== ]          [EPA / nota]
[W2 contagem ====  ]
[legenda de volume observado e limites]
```
Gráfico principal mostra contagens de members; não eficiência, ritmo ou tendência. Não há rotas, formações, posições ou mapa de calor. Campo é moldura, com aviso de cenário esquemático.

## Contrato dos gráficos
| Gráfico | Pergunta / campos | Denominador | Risco evitado | Alternativa textual |
| --- | --- | --- | --- | --- |
| A composição de sucesso | Quantas jogadas com EPA foram positivas? totals.successN e epaN; values.successRate | epaN | Resto = EPA zero OU negativo; não todas negativas, não total eligible | Contagens, percentual e dois rótulos visíveis + nome acessível |
| B duas faixas | Como se divide a população EPA? successN e epaN-successN (BigInt) | epaN, escala explícita | Não sugerir comparação entre equipes nem qualidade | Contagens e frações ao lado das faixas |
| C volume por jogo | Quantas jogadas deste recorte constam em cada jogo? members.statistics.eligibleN | totals.eligibleN apenas para geometria de participação | Não tendência, ritmo ou total completo; ausentes ficam sem barra | Lista de IDs, semana, contagens e estado da fonte |
| Frequência secundária | Qual a participação do fundamento? values.frequency, totals.generalEligibleN | generalEligibleN da mesma observação | Complemento chamado outras jogadas classificadas, sem inferir outro fundamento | Razão exata em contagens, proporção e legenda |

Gráficos indisponíveis com denominador zero; valores pequenos positivos recebem texto, nunca mínimo visual fabricado. C mantém barras de contagem zero conhecidas e fontes ausentes separadas.

## Critérios de crítica
Três estruturas reconhecíveis sem ler o nome; gráfico visível junto ao primeiro fato; mesma observação na troca A/B/C; fundamentos a um clique; limite do modelo junto ao EPA/sucesso; nenhum jargão operacional no caminho principal. Testar 1440×900,1024,390×844,320,texto200%, teclado e movimento reduzido. Criticar cada direção e refiná-la antes da captura final. Todas continuam disponíveis; decisão do usuário posterior.
