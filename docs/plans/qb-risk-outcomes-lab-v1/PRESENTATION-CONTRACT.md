# Duas perguntas, dois alvos

Base visual aprovada `5d7d7769ce71a6864edce4c7393a75913563595f`, ancestral confirmado da pesquisa B2 `a2466636dec1d7feb8c3975cf984d7b505711dde`. Nova worktree/branch isolada; sem merge de branches divergentes.

Preservar ardósia `#15232c`, painel `#d6e1e6`, área do gráfico `#eaf0f3`, tinta `#355c71`, seleção `#d7f56b`, texto claro `#d8e3e9`. Archivo em títulos, Roboto Condensed em números e identidade. Alinhamento à esquerda; gráfico retangular na largura útil, sem nomes/caixas/linhas-guia permanentes. A composição aprovada governa a direção visual; não há novo sistema de marca.

```text
Laboratório
Risco dos passes                 Interceptações sofridas
pergunta curta                   pergunta curta
título da leitura ativa + significado do alvo
cobertura/modelo da fonte ativa
período / unidade / posição
gráfico amplo + identificação sob demanda
resumo do jogador / lista completa
detalhe + conta B2 + jogos + quatro cruzamentos + evidências
metodologia expansível
```

`reading=passes` = M3; `reading=interceptions` = B2. Ausência do parâmetro conserva M3. Troca preserva parâmetros existentes, jogador, período, escala e posição; não seleciona substitutos. Ausência na fonte ativa fica explícita; nenhum número da outra leitura permanece. Cada leitura mantém seu pacote imutável durante a sessão; conferir versão é uma ação explícita. Detalhes sempre usam o ID do índice carregado.

M3: alvo classificação FTN, expectativas e previsões preservadas. B2: alvo INT observada; campos `expectedInterceptions`, `observedInterceptions`, `expectedFromClassified`, `expectedFromNotClassified`. Não converter B2 no contrato M3 com aliases `expected`/`observed`. Elementos geométricos podem compartilhar x/y; a semântica e os textos continuam explícitos.

B2 soma as probabilidades do pacote científico, sem ajuste: 305/553 e 75/16805 são taxas fixas de 2025 verificadas contra o modelo JSON pinado. A conta exibida usa as quantidades do jogador/período, soma sem arredondamento intermediário e mostra valores arredondados só na apresentação. Mesma taxa para todos os passes de uma classe, sem dificuldade individualizada. Perto do gráfico: retrospectivo e sem atribuição causal. Na metodologia: FTN pode conhecer o resultado, calibração FTN=0 em 2025 de 75 observadas/52,92 esperadas e distinção de M3.

A skill frontend-design orienta preservar o caráter específico já aprovado. A consulta UI/UX Pro Max `keyboard focus navigation continuity` retornou navegação completa por teclado, foco visível e não encoberto; aplicar à navegação, pontos, nomes próximos e evidências. A prévia permanece sob os eixos em telas estreitas/texto ampliado. Teclado/toque/lista permitem alcançar pontos coincidentes sem deslocar coordenadas ou somar jogadores.

Nenhum dado B2 entra em `public/data`; entrada e build locais separados. Atualização manual aplica o modelo fixo em outra aquisição, valida, cria pacote imutável e troca somente o ponteiro B2 atomicamente. Falha preserva a versão anterior; M3 é leitura apenas.
