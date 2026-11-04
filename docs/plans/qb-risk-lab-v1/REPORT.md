# Laboratório — entrega local

A implementação está navegável e atualizável manualmente. A pergunta inicial conduz à comparação FTN/modelo, ao detalhe por GSIS e às evidências de cada passe. O M3 foi aplicado sem treino, busca ou recalibração. A [decisão datada](DECISION.md) substitui a espera W9–13; o protocolo anterior continua preservado, e estes resultados são exploração contínua.

## Observado e estimado

A aquisição de 04/11/2026 encontrou **121 jogos encerrados e utilizáveis, W1–8**, sem jogo encerrado pendente. São 7.970 passes elegíveis e 66 lançadores: 57 QBs identificados e 9 de outras posições. 151 jogos ainda sem resultado final não entram no agregado.

- **Observado:** 242 rótulos interceptáveis FTN (3,0364%) e 170 interceptações reais, em colunas/conceitos separados.
- **Estimado:** 253,2163 passes interceptáveis pela soma das probabilidades M3 (3,1771%). Diferença total −11,2163, ou −0,1407 por 100 passes.
- **Desconhecido:** quanto desse residual vem de contexto omitido, execução, charting ou variação; a persistência por jogador; a calibração futura e a completude de revisões ainda não publicadas.

O exemplo Daniel Jones acumula 267 passes/8 jogos, 17 rótulos FTN, 8,6601 esperados e 9 INT. A interface usa os valores selecionados para explicar o cálculo; a ordenação é uma ordenação do número, sem julgamento de qualidade. Nenhum intervalo comparativo por jogador foi acrescentado. O corte inicial de 100 passes é convenção exploratória, com acesso explícito a todos os volumes e lançadores. Selecionar uma semana muda o volume para “todos” para não esconder os passes semanais sob um corte pensado para o acumulado.

[Dados,exclusões,joins,identidades,licenças e todas as semanas](DATA-COVERAGE.md) · [reconciliação independente](evidence/reconciliation.json).

## Modelo e pacote

M3 `M3-2026-frozen-v2`, estrutura 2023–24, offset −0,1593395890254225 calibrado somente em 2025. SHA-256 do JSON congelado:
`38b9933535dada0f8b0ed22842ef247fe8e9beeca2a4c3469f4abc54b2b535a6`.

Pipeline 1.0.0, pacote ativo `d3739e3d9103c48fda1c417a`, índice SHA:
`05ae0b8771a4705bc3ca6b448e7f8f7b8ea13d7e0446b8256fb2ac67f1dc8f24`.

Features permanecem descida, distância, posição de campo, quarto, relógio e diferença pré-jogada, com preprocessing/coeficientes congelados. Sem identidade, air_yards, EPA, INT ou resultado como features. Serialização JSON confiável e pinada; nenhum pickle ou modelo baixado é carregado. A interpretação segue o model card v2; esta entrega não produz nova evidência independente de utilidade preditiva nem certifica o modelo para produção.

## Funcionamento e preservação

A atualização tem lock exclusivo, cópias próprias, validadores globais e por jogo, recibos de revisão e ponteiro final por `os.replace`. Jogo incompleto fica inteiro fora e aparece como lacuna; corrupção estrutural impede substituir a versão válida. Pacotes anteriores continuam disponíveis, permitindo que uma página já aberta consulte seus detalhes sem misturar a versão nova. Uma atualização sem mudança semântica mantém o pacote; mudanças históricas de rótulo ficam explícitas no recibo.

A experiência nova reutiliza ardósia, papel, Archivo, Roboto Condensed, logos e cores aprovadas. O acesso ao laboratório é opt-in na cópia do cabeçalho do acervo; a entrada anterior mantém o comportamento padrão. Hub, confrontos, times e referências continuam acessíveis. Builds públicos normais, snapshots, contrato, backend, ETL e pesquisas anteriores não foram modificados. Os cinco arquivos do build público são **idênticos em bytes** ao checkout aprovado; [prova objetiva](evidence/isolation.json).

O build separado contém 209 documentos GET congelados, com mapas de headers e hashes, sem copiar `public/data`. Está preparado para revisão de hospedagem futura: o servidor local de preview comprova os endpoints. Uma publicação posterior precisa mapear os endpoints/headers e revisar as obrigações de atribuição/ShareAlike; não houve deploy, push, merge ou publicação externa.

## Verificação e tentativas relevantes

Os testes e inspeções estão detalhados em [VERIFICATION.md](VERIFICATION.md). Reprodução em destino novo, com outro ambiente e sem rede: [recibo](evidence/reproduction.json). O arquivo de recuperação contém fontes, modelo, ambiente, build e recibos; todos os membros foram conferidos por hash: [recuperação](evidence/recovery.json). São provas desta execução, sem promessa de identidade universal de ambientes.

A primeira aquisição terminou com erro de montagem do resumo por jogo (`dict` com chaves repetidas); nenhum pacote foi ativado. As fontes válidas foram preservadas e reusadas após corrigir a montagem. O erro está em `runs/20261104T144706530236Z/failure.json`. Fixtures iniciais precisaram retornar array NumPy; a coleta combinada de testes revelou conflito do import genérico `pipeline`, resolvido no import do teste novo, sem alterar v1/v2. O primeiro build TypeScript apontou ausência de tipos Node, instalados apenas como dependência dev nesta worktree. A inspeção 320 px/texto 200% revelou overflow nos cruzamentos; a correção de grid e números foi verificada novamente. Nenhuma dessas correções mudou o modelo ou o alvo.

## Limites e próximo ajuste

A completude auditada do join não certifica a verdade da avaliaçãoFTN. Pequenas diferenças agregadas não justificam precisão individual. O modelo não observa pressão efetiva, defensores, alternativas de recebedores ou atribuição de responsabilidade. Não se deve interpretar resíduo como decisão causal nem usar a ordenação como ranking de inteligência ou habilidade.

Próxima ação operacional: revisar a leitura visual e atualizar manualmente quando houver novos jogos utilizáveis, conferindo lacunas e recibos. Próximo trabalho de pesquisa deve definir uma nova pergunta/protocolo antes de mudar o M3. Atualizar dados e mudar modelo continuam operações distintas.
