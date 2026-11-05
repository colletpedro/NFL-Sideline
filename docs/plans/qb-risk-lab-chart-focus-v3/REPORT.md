# Relatório — composição e interação do gráfico coletivo

A distribuição passa a ocupar toda a largura útil do conteúdo. Foram removidas as identificações permanentes e as linhas-guia; a identidade aparece por hover, foco ou seleção. A comunicação aprovada dos três números permanece. O M3 continua estimando passes classificados como interceptáveis, sem estimar interceptações sofridas.

## Comparação com a referência

Comparação real no navegador, em 05/11/2026, com a referência 18123 e a versão 18124 a 1440 px. [Antes](captures/before-desktop.png) · [Depois](captures/after-desktop.png).

| Composição anterior | Composição v3 |
|---|---|
| Gráfico estreitado pelo resumo/lista lateral | Gráfico com 100% da largura útil; resumo e lista abaixo |
| Painel quadrado alto no desktop | Projeção retangular com altura de dados limitada a 440 px |
| Caixas de nomes/quantidades e linhas-guia sempre visíveis | Somente pontos, grade discreta, eixos e igualdade no estado inicial |
| Grupos permanentes dependentes da largura | Nomes próximos disponíveis durante a interação, sem agregação |
| Período e controles em blocos separados | Barra local compacta, sem acrescentar controles |
| Legenda concentrada na igualdade | Orientação aberta para direita, acima e diagonal, adaptada à unidade |

A distribuição é visível sem escolher um jogador. A escala continua incluindo todos os valores, inclusive os extremos de amostra curta. A linha representa igualdade numérica em todo o domínio; sua inclinação visual muda com a proporção do painel. Não ajustamos uma regressão nem deslocamos pontos.

## Interação e leitura

Mais à direita significa maior expectativa de passes interceptáveis para os contextos dos passes; não significa, sozinho, pior desempenho. Mais acima significa mais classificações interceptáveis da FTN. Acima da linha, mais que o esperado; abaixo, menos. Totais dependem também do volume. Por 100 usa o mesmo denominador e unidade nos dois eixos e troca as explicações por taxas.

Hover não altera seleção/URL e não solicita evidências de outros jogadores. A prévia traz logo, nome, equipes, classificados/esperados com unidade e suporte. Clique ou Enter/Espaço selecionam imediatamente, mantendo os demais pontos. Há contorno/estado textual de seleção, sem depender só de cor. O resumo conserva os três nomes completos e os totais do mesmo período; o acesso ao aprofundamento é explícito, sem rolagem automática da página ao selecionar um ponto. Apenas a rolagem interna da lista acompanha o nome selecionado.

Daniel Jones: 267 passes, 8 jogos, 17 classificados como interceptáveis, 8,660127799064037 esperados e 9 interceptações sofridas. Na W8: 28 passes, 2 classificados, aproximadamente 1,03 esperado e 2 interceptações. Anthony Richardson, também IND: 2 passes, 1 jogo, 0 classificados, aproximadamente 0,14 esperado e 0 interceptações. Identificadores estáveis mantêm ambos separados. Bo Nix, perto da igualdade: 8 classificados e aproximadamente 7,96 esperados em 250 passes. Esses são exemplos de leitura, sem ranking de habilidade.

Pontos próximos conservam suas coordenadas. A interação oferece seus integrantes, com nomes e logos, sem somar estatísticas. A seta para baixo leva do ponto aos botões de integrantes. No navegador foi possível selecionar outro lançador dessa região pelo teclado. Coincidências numéricas exatas são verificadas por fixtures; os dados reais incluem pontos separados por frações de pixel, sem fabricar coincidências.

Uma URL antiga com `player=00-0035710&group=00-0039164` mantém Daniel selecionado, explica a marca associada a Anthony e apresenta a lista inteira. Recarregar, voltar e avançar preservaram o estado. Grupo sem jogador não gera seleção automática. O link antigo da evidência `2026_08_IND_JAX:2125` continua aberto após recarga, com classificação e interceptação separadas.

## Refinamento visual executado

Desktop amplo e intermediário, 390 e 320 px foram conferidos. O primeiro desenho de prévia flutuante ficou apertado a 200% no celular. A versão final usa uma prévia no fluxo abaixo dos eixos em telas estreitas ou com texto ampliado, sem cobrir a distribuição. O cabeçalho da prévia amplia e reorganiza nome/logo/fechamento; os nomes próximos têm rolagem vertical própria. No desktop, a prévia é limitada ao painel e posicionada acima/abaixo do ponto, mantendo o ponto de origem descoberto.

A revisão avaliou tamanho útil, densidade, nomes, hierarquia e continuidade; ausência de overflow foi apenas um dos critérios. A lista completa abaixo é a alternativa permanente ao gráfico. Sua organização usa três colunas no desktop, duas em largura intermediária e uma no celular. Não houve teste com participantes humanos nem auditoria exaustiva com leitor de tela.

## Verificação e preservação

Suíte completa com fontes locais: **400 resultados esperados: 395 passes normais e 5 expected failures legados; zero skips e zero falhas inesperadas**. São oito casos adicionais em relação à v2. Os cinco `it.fails` mantêm os mesmos bytes e expectativas. TypeScript e os dois builds passaram. Lint: zero erros e um warning legado em `reading-polish/main.tsx`.

Testes cobrem projeção retangular, igualdade, unidades, denominadores, ausência de identificações permanentes, hover sem efeito na URL/seleção/fetch, clique, eventos de toque, teclado, coincidências, proximidade sem encadeamento, resumo e período, URLs antigas com grupo, histórico, respostas tardias, zero eventos, ausência de passes, falha e retry. Os testes antigos de caixas permanentes foram adaptados ao novo comportamento; as verificações de dados e expected failures foram preservadas.

[Reconciliação independente](evidence/browser-reconciliation.json): 14 estados do navegador e 733 coordenadas, com somas por passe das evidências congeladas. Tolerâncias: coordenadas `1e-10`, projeção SVG `1e-8`, números exibidos 0,005 pelo arredondamento. Também são conferidos prévia/unidade, integrantes próximos, largura integral e ausência de identificações permanentes.

[Preservação](evidence/preservation.json): M3 SHA `38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6`; pacote `d3739e3d9103c48fda1c417a`, seus 70 arquivos e ponteiro ativo mantidos. Quatro fontes brutas, previsões por passe e 209 documentos GET do build mantêm seus hashes. O build público normal mantém os mesmos bytes. `model.ts` (contrato/agregação), `Metrics.tsx`, pesquisa, backend, ETL, snapshots, contratos e documentos anteriores têm diff vazio. As referências v2 e site aprovado permanecem limpas em seus HEADs originais.

## Limites e ocorrências da conferência

O navegador disponibilizado recusou `Input.dispatchTouchEvent`. Por isso o toque foi verificado por `PointerEvent(pointerType=touch)` e clique sintetizado no handler real, além dos testes offline. Isso confirma o comportamento da aplicação, sem alegar teste de gesto nativo em dispositivo físico. [Recibo](evidence/touch-emulation.json). Rede artificial, emulação de movimento e fonte ampliada foram restauradas ao final.

A primeira checagem TypeScript apontou testes da geometria antiga; após adaptar a projeção/identificação, duas expectativas de seletores antigos foram corrigidas. Não foram transformadas em skips ou expected failures. Uma navegação de QA com ID inválido foi recusada corretamente; a seleção de Bo Nix foi refeita pela interface. Um seletor exato do label Período não encontrou o controle no driver; a conferência prosseguiu pelo ID estável do select. Essas ocorrências não alteraram os dados para acomodar o teste.

A região perto de zero continua densa e requer a prévia/lista para identificar integrantes. Não há jitter, corte de volume ou garantia de robustez acima de 100 passes. O residual continua sem interpretação causal de decisão, culpa ou habilidade.

[Operação e reprodução](README.md) · [Capturas e estados](CAPTURES.md) · [Testes](evidence/checks.json). Sem merge, push, deploy, publicação externa ou encerramento de servidores anteriores.
