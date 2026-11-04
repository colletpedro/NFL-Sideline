# Relatório — comunicação e visão coletiva

A entrega corrige a ambiguidade relatada pelo usuário e acrescenta um gráfico coletivo, sem mudar a pesquisa. A abertura explica que **passes interceptáveis não são interceptações**, apresenta FTN como provedora da classificação e diz explicitamente que o M3 estima passes interceptáveis, não interceptações sofridas. Isso permanece visível em links diretos de jogador.

## Antes e depois

| Antes | Agora |
|---|---|
| “FTN · observados” e “Modelo · esperados” permitiam confundir o alvo com interceptações | Rótulos completos: passes classificados como interceptáveis; passes interceptáveis esperados; interceptações sofridas |
| Comparações individuais, 33 QBs no corte inicial de 100 passes | Gráfico coletivo com 57 QBs identificados, sem corte; 66 lançadores na opção explícita de todas as posições |
| Interceptações em bloco separado e distante | Os três números juntos no resumo selecionado e no detalhe |
| Sem referência coletiva de igualdade | Eixos na mesma unidade/domínio, diagonal “Observado = esperado”, regiões explicadas |
| Expectativa decimal sem explicação imediata no detalhe | Soma de probabilidades, distinta de uma fração de evento ocorrido |

[A captura anterior preservada](captures/before-v1.png) é cópia exata da evidência versionada em `8e98296`, não uma simulação do “antes”. [Abertura nova](captures/opening-1440.png) · [Visão coletiva e Daniel Jones](captures/collective-daniel-1440.png).

## Como ler e exemplos

Horizontal: **passes interceptáveis esperados**. Vertical: **passes classificados como interceptáveis**. Acima da diagonal, mais classificados como interceptáveis que a referência contextual esperava; abaixo, menos. A diagonal é uma identidade matemática, não desempenho ideal, decisão correta ou interceptações merecidas. Totais dependem também do volume. Na escala por 100, ambos usam os passes elegíveis do mesmo jogador e período.

Daniel Jones, no acumulado congelado: 267 passes em 8 jogos, 17 passes classificados como interceptáveis, 8,660127799064037 esperados e 9 interceptações sofridas. A leitura é: FTN classificou 17; para os contextos desses 267 passes, M3 somava cerca de 8,66 probabilidades; 9 passes terminaram em interceptação. A diferença entre classificação e interceptações **não** é apresentada como interceptações derrubadas.

Na W8, o mesmo jogador tem 28 passes, 2 classificados como interceptáveis, cerca de 1,03 esperado e 2 interceptações sofridas. Todos os números trocam juntos com o período. O cruzamento “não classificado como interceptável · com interceptação” contém a evidência `2026_08_IND_JAX:2125`, preservada e acessível por URL antiga, Enter, voltar, avançar e recarregar.

Anthony Richardson compartilha IND com Daniel, mas tem GSIS próprio e somente 2 passes, 0 classificados, cerca de 0,14 esperado e 0 interceptações. Logo e nome juntos evitam identificar ambos somente pela equipe. Na W7, sem passes dele na população selecionada, a apresentação mostra travessões e explica a ausência de denominador; não inventa uma comparação de risco.

## Identificação e interação

Nenhuma coordenada estatística é deslocada. Grupos limitam a proximidade ao ponto inicial, sem encadear uma nuvem inteira em um único grupo. Linhas-guia ligam identificações às coordenadas. No celular, marcas com a quantidade de jogadores e a lista sincronizada evitam comprimir todos os nomes. O número do grupo é a quantidade de integrantes; suas estatísticas não são somadas. Cada integrante continua selecionável por nome, equipe e identificador estável. Círculos vazados sinalizam menos de 100 passes como convenção de leitura; não certificam robustez dos demais.

Selecionar jogador destaca seu círculo, mantém os outros pontos e mostra os três números do período. O detalhe/evidências carrega imediatamente, sem botão de aplicar. Grupos abrem seus integrantes e limpam a seleção individual anterior. A escala e os grupos são estado de URL, mas parâmetros novos não são obrigatórios para links antigos. Equipes múltiplas são mantidas na identidade e indicadas por logos/códigos; fixtures cobrem troca de equipe e posição desconhecida.

## Conferências executadas

A suíte configurada inclui os 68 testes condicionais que a execução simples pulava. Total: **392 resultados esperados pelo Vitest: 387 passes normais e 5 expected failures legados; 0 skips e 0 falhas inesperadas**. Os cinco `it.fails` e suas expectativas não foram editados. São 379 casos anteriores mais 13 novos. [Resumo](evidence/checks.json), [log](checks/frontend.log), [JSON](checks/frontend.json). TypeScript passou; lint tem 0 erros e 1 warning legado em `reading-polish/main.tsx`. Builds público e separado passaram.

Os testes novos verificam coordenadas, projeção SVG, domínio e igualdade, normalização, mesmo período/denominador, zero eventos, ausência de passes, amostra curta, coincidência exata, ausência de encadeamento, labels sem sobreposição, todos os IDs, equipes múltiplas, determinismo e seleção por teclado. As regressões de URL, histórico, evidência direta, retry e resposta tardia continuam verificadas numericamente. A conferência com fontes reais recalcula somas das evidências por passe para todos os jogadores, semanas disponíveis e escalas; não se limita a snapshots de HTML.

Recibos do navegador foram reconciliados independentemente com as evidências congeladas: 13 estados e 676 coordenadas de jogador, mais os resumos e denominadores apresentados. [Dados lidos no DOM](evidence/browser-cases.json) · [recibo](evidence/browser-reconciliation.json). Coordenadas/unidades: tolerância `1e-10`; projeção SVG `1e-8`; valores exibidos 0,005 pelo arredondamento. O agrupamento de proximidade não altera os valores.

Inspeção real: abertura sem seleção, Daniel, Anthony da mesma equipe, amostra curta, grupo de pontos visualmente próximos, teclado, URLs antigas, 1440/390/320 px, texto 200%, carregamento e falha. Em 320 px, o documento tem 305 px úteis e 305 px de scroll; com texto 200%, os ticks também ampliam de 13 para 26 px, sem overflow horizontal. Foco de marca no SVG é visível com stroke 4 px. Rede, tamanho de texto e viewport temporários foram restaurados. [Foco](evidence/keyboard.json). [Capturas de conferência](CAPTURES.md).

Coincidências numéricas exatas foram exercitadas em fixtures; no navegador, o pacote real fornece pontos muito próximos, inclusive eventos zero com expectativas separadas por frações de pixel. Não fabricamos um caso NFL para ilustrar coincidência.

## Prova de preservação

[Recibo de preservação](evidence/preservation.json): o modelo JSON M3 conserva SHA `38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6`; pacote `d3739e3d9103c48fda1c417a`, 70 arquivos e ponteiro ativo sem mudança. As 4 fontes brutas mantêm seus hashes. Os 209 documentos de dados do build compilado continuam idênticos aos da recuperação v1. Também permanecem iguais os 5 arquivos do build público normal.

Pesquisa, previsões por passe, resultados científicos, fontes pinadas, contrato público, snapshots, backend, ETL e documentos anteriores têm diff vazio. Checkout original permanece limpo em `8e98296`; o site aprovado também permanece limpo em `5b38f04`. O fluxo de atualização manual continua preservado e não foi acionado. Nenhum novo modelo ou avaliação independente foi alegado.

## Revisão técnica de comunicação

| Pergunta | Evidência da resposta |
|---|---|
| Está explícito que o modelo estima passes interceptáveis? | Texto essencial visível e eixos com unidade completa; probabilidade da evidência nomeia a classificação |
| As interceptações reais são encontráveis? | Terceiro número adjacente nos dois resumos, na lista e no jogo a jogo |
| Igualdade parece “decisão correta”? | Legenda define igualdade numérica de classificação/estimativa e explica acima/abaixo; nenhuma regressão ou rótulo de qualidade |
| Os números usam o mesmo período? | Reconciliação por passe em cada semana e alteração dos três valores; filtro de evidência por jogo explicado separadamente |
| Cada QB pode ser identificado? | Logo+nome, GSIS interno, grupos com integrantes, lista e teclado; sem depender de hover |
| Volume aparece na interpretação? | Aviso junto do gráfico, passes/jogos por jogador e amostra curta visível |
| A explicação essencial está visível sem metodologia? | Os dois parágrafos iniciais permanecem abertos em visão coletiva e URL direta |

Esta é uma revisão técnica, não um teste com participantes humanos nem evidência de compreensão garantida.

## Limitações e próximos ajustes

O gráfico permanece denso perto de zero; identificação completa nesses locais depende das marcas e da lista. Grupos mudam com espaço/unidade e são recursos de interação, não categorias estatísticas. A lista tem rolagem vertical própria. Não houve auditoria exaustiva com leitor de tela.

O M3 continua experimental e estima o rótulo do provedor. Seu resíduo não atribui causalmente decisão, culpa, inteligência ou habilidade. A pergunta futura sobre interceptações sofridas em relação ao risco dos passes permanece sem modelo; não há linha de “interceptações esperadas”. A revisão visual do usuário pode orientar novos ajustes de densidade/comunicação, sem alterar dados ou transformar a pesquisa em ranking de qualidade.

[Operação, testes e encerramento](README.md). Nenhum servidor anterior foi encerrado; 18123 é separado e estrito. Sem merge, push, deploy ou publicação externa.
