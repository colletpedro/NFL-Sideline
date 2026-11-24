# Integração — Progressão e improvisação

Entrega funcional em 06/11/2026, pronta para aceite visual posterior. A nova leitura foi acrescentada ao laboratório M3/B2 em uma worktree isolada derivada exatamente da pesquisa aprovada. Não houve nova aquisição, modelo, retreino ou publicação.

## DES: antes e depois

A classificação 2.0.0 mantém a checagem de conflitos/abortos antes de aplicar sack → scramble verificado → throwaway → passe SD → progressão → DES → residual. O classificador auditado v1 é reaplicado primeiro; só `indeterminate` com motivo `designed_no_progression`, em lançamento válido, migra para `designed`. Caso abortado/conflitante com código DES continua residual. Flags brutas, regra/motivo, tipo de evento, identificação, EPA e referências permanecem; categoria e regra anteriores também são guardadas.

| 2026 | Residual v1 | DES próprio v2 | Residual verdadeiro v2 |
| --- | ---: | ---: | ---: |
| Todos os participantes | 799 | 797 | 2 |
| Somente QB auditados | 791 | 790 | 1 |

Os dois residuais atuais são um aborto e um scramble atribuído a WR. O GSIS do WR continua identificado como outra posição, sem chamar esse caso de scramble de QB. Não houve diferença em relação às pistas de reconciliação; esses números são resultados, não constantes do classificador.

No conjunto elementar das cinco temporadas, 7.986 DES foram separados; 2022 continua auditoria, sem integração à comparação principal histórica. População: 89.715 linhas elementares, das quais 69.505 principais em 2023–2026. As chaves, EPA e identidade foram preservados exatamente. O contrato de consumo sobe para esquema 2, rejeitado por/para leitores incompatíveis; a métrica principal permanece 1.0.0 porque A/B não mudou. A pesquisa e pacote v1 não foram reescritos.

## Resultado científico preservado

2026: 8.962 dropbacks em 121 jogos REG W1–8, até 02/11/2026; todos com FTN e EPA. São 8.951 dropbacks de 57 QB e 11 eventos de outras posições, todos consultáveis. Sem exigir rodada completa. A liga pondera jogadas dos QB auditados, sem média simples das médias dos jogadores.

| Jogador | n A / B | EPA/jogada A / B | Diferença A−B |
| --- | ---: | ---: | ---: |
| Mahomes | 153 / 32 | 0,371 / −0,021 | +0,392 |
| Maye | 174 / 51 | 0,297 / 0,966 | −0,670 |
| Willis | 137 / 42 | 0,235 / 0,231 | +0,005 |
| Stroud | 194 / 28 | 0,295 / 0,700 | −0,405 |
| Stafford | 265 / 7 | 0,210 / −0,292 | +0,502 |

Esses valores vêm dos artefatos, não de constantes no frontend. A liga permanece A=0,230 (6.340) e B=0,309 (909). Throwaways e sacks continuam em blocos próprios. Em Stroud, a diferença muda para +0,037 com descartes e +0,635 com descartes+sacks; a tabela opcional mostra simultaneamente as quatro definições e volumes. A versão só com passes SD tem pouco suporte em muitos casos.

### Diagnóstico adicional: progressão + DES

Somas e n EPA válidos foram combinados, sem média simples das médias. Isso é um diagnóstico do lado planejado, não nova comparação principal nem controle obrigatório da interface.

| Temporada QB | n progressão | n DES | EPA progressão | EPA DES | EPA progressão+DES |
| --- | ---: | ---: | ---: | ---: | ---: |
| 2023 | 14.372 | 1.918 | 0,172 | −0,079 | 0,142 |
| 2024 | 13.866 | 1.954 | 0,224 | 0,022 | 0,199 |
| 2025 | 13.956 | 1.664 | 0,221 | −0,010 | 0,197 |
| 2026 | 6.340 | 790 | 0,230 | −0,043 | 0,200 |

Em 2026, progressão+DES tem 7.130 oportunidades e média 0,199827; a diferença contra B seria −0,108859, comparada a −0,078586 na principal. O efeito não autoriza substituir A silenciosamente. [Precisão integral](evidence/planned-diagnostic.json).

## Comunicação e interação

Abertura explica progressão, improvisação identificada e EPA sem começar por códigos técnicos. Os eixos são EPA/jogada em improvisação no horizontal e EPA/jogada em progressão no vertical; direita/acima indicam maior produção média na respectiva condição. Média da liga por condição e diagonal de mesma média são explicadas, sem rótulos de quadrantes.

Não aplicamos o antigo corte científico como filtro: os 52 QB com duas médias disponíveis aparecem; os cinco sem oportunidade em um eixo continuam na lista, sem coordenada zero. Círculos vazados identificam pouco suporte. Hover/foco mostra nome/logo/volumes; clique, toque emulado e teclado selecionam sem deslocar pontos ou rolar a página. A região densa oferece nomes individuais; ArrowDown no ponto alcança a lista. Nos 390/320 px ou fonte ampliada, a prévia passa para baixo do gráfico. Os ticks são reduzidos conforme largura/fonte, sem mudar valores/coordenadas científicas.

O resumo mostra A/B com volumes, frequência “X de N dropbacks” e diferença secundária. Composição expõe as sete categorias com quantidade, percentual sobre todos os dropbacks, EPA médio/soma/n válido e acesso às jogadas. DES se chama “Lançamentos desenhados”, sem ser descrito como dado ausente. Indeterminados mostram seus motivos reais. Sensibilidades ficam em aprofundamento opcional; A permanece fixo.

Evidências filtráveis por categoria mantêm os totais do período. Incluem jogo/jogada estável, semana, situação, relógio, campo, EPA, regra, motivo, descrição literal e indicadores originais. Todas as jogadas ficam acessíveis por paginação; uma evidência direta abre sua linha, e filtro/seleção/período são restaurados pela URL. Sem inferência de intenção ou responsabilidade pelo texto.

As três leituras conservam jogador e período válidos. Ausência de fonte/oportunidades é explícita. O controle por 100 permanece somente no M3/B2; um parâmetro herdado não multiplica EPA. Cada sessão conserva seu packageId até refresh explícito, e respostas tardias não misturam leituras/jogadores/versões.

## Verificação e refinamento

| Camada | Evidência |
| --- | --- |
| Fontes → classificação | SQL independente dos brutos, chaves/EPA e DES auditado; sem alteração da população |
| v1 → v2 | A/B e quatro sensibilidades com chaves/EPA exatos; identidade preservada |
| Pacote → HTTP | Índice e todos os 68 detalhes idênticos aos arquivos, com integridade e versão estritas |
| HTTP/pacote → interface | Cinco exemplos reais, todas as categorias e 260 coordenadas observadas reconciliadas a 1e−12 |
| Períodos | 612 combinações jogador/período conferidas contra jogadas, sem rateio |
| Navegador | Desktop 1440, 390/320, texto 200% em 320, hover, teclado, região densa, baixo suporte, ausência, DES, sensibilidades, evidência direta, histórico/recarga e recuperação de falha |
| Atualização | Replay byte a byte em store de QA; guarda de regra fixa antes da aquisição; falha de troca preserva ponteiro e recuperação validada |

425 resultados frontend aprovados: 420 comuns, cinco expected failures legados, zero falhas inesperadas e zero skips. Python novo: 15 passes. Preservados: M3 23, B2 33, pesquisa v1 42. TypeScript passa; lint sem erros, com um warning preexistente. [Resumo](evidence/qa-summary.json).

Refinamentos observados: navegação de três perguntas empilhada em telas estreitas; prévia deslocada para fora do gráfico com fonte ampliada; menos ticks para evitar rótulos sobrepostos em 320/200%; singular/plural nos volumes pequenos. O toque foi sintetizado com PointerEvent de tipo touch e clique, não em dispositivo físico; a seleção de Stafford conservou scrollY=1180,5 antes/depois. O bloqueio de rede de QA foi removido, fonte/viewport restaurados e a aba entregue. Não há garantia universal de acessibilidade por essas verificações.

## Preservação e limites

M3/B2 mantêm parâmetros, previsões, fontes, pacotes e ponteiros; 16.095 arquivos do store M3 e 233 do B2 permaneceram idênticos. Os 257 arquivos manifestados da pesquisa v1 e fontes pinadas também. O build público tem cinco arquivos idênticos em bytes à referência, sem interface/dados desta leitura. Backend, banco, ETL, contratos públicos e snapshots não foram alterados. A porta 18125 não respondia antes/depois e não foi reiniciada; somente o novo loopback 18127 foi iniciado. A configuração inicial deste novo processo estava sem os três configs locais do hub; foi corrigida e somente o processo desta entrega reiniciado. O log final valida 262 turnovers, 107 placares/confrontos e 32 times; o hub W1–7 foi conferido no navegador sem alertas.

EPA continua produção observada do ataque, não contribuição causal isolada do QB. Contextos de A/B diferem; classificação retrospectiva, diferenças históricas, poucas oportunidades e extremos limitam a comparação. Não há nova demonstração de habilidade persistente nem ranking de dependência do sistema. A integração funcional não substitui o aceite visual do usuário.

[Operação, atualização e encerramento](README.md) · [Capturas](CAPTURES.md) · [reconciliação completa](evidence/reconciliation.json) · [preservação](evidence/preservation-summary.json).
