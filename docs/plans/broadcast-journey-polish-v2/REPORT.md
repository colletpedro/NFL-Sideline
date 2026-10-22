# Percurso guiado v2 · acabamento da experiência local

Base exata `46e2252476738c8240a26b38242e66ca20a75d42`, nova worktree e branch `codex/broadcast-journey-polish-v2`. Implementação e regressões no commit local `150bf9a`. Candidata à avaliação visual do usuário, sem merge, push ou deploy.

## O que mudou

O confronto deixa de oferecer uma lista de todas as observações. Os painéis dos times viraram botões explícitos, com “Selecionar time”/“Selecionado”, foco e `aria-pressed`. A pessoa escolhe ataque ou defesa e fundamento; uma opção principal abre a amostra correspondente. A seleção inicial é visível e não abre automaticamente uma observação. Não existe recomendação de time ou desempenho nessa escolha.

A escolha do time usa `team`, a do lado `side` e a do fundamento `play` na URL, junto de temporada, semana e filtro. Na leitura, o documento nominal continua prevalecendo sobre essas preferências: mudar uma preferência não altera a observação aberta até clicar na ação de abertura. Retorno, histórico e recarga preservam o contexto.

Períodos inclusivos, outros períodos e outra temporada/fase aparecem somente quando existem e ficam recolhidos. Cada item preserva seu período e sua classificação. Lacuna possui ação explícita “Ver lacuna”, sem números, barras ou substituição por outra semana. Um time sem leitura exclusiva recebe orientação e somente os outros períodos efetivamente disponíveis.

Na central, o primeiro jogo com observação individual ganha destaque; se nenhum existir, mantém-se o primeiro da seleção. Isso prioriza um destino utilizável, sem avaliar desempenho esportivo. O destaque foi retirado da lista subsequente. Foram removidos nomes repetidos na abertura, e os controles de calendário dividem melhor o espaço no mobile.

Na observação, o vínculo com a partida ocupa uma faixa curta antes da identidade. A apresentação `guided`, opcional e desligada por padrão no componente compartilhado `Reading`, retira a manchete que repetia a contagem do gráfico quando há jogadas elegíveis. EPA, volume e gráfico aparecem primeiro; modelos, denominadores, limites, contagens e origem continuam disponíveis. Ausência e amostra vazia mantêm suas explicações específicas. A entrada real anterior continua sem essa opção.

## Comparação medida no navegador

Mesmo confronto BAL–IND, defesa contra passe, fonte raiz 16 px. A extensão inclui a página inteira, com detalhes recolhidos. São medidas de layout, sem inferência sobre compreensão humana.

| Medida | Antes | Depois |
|---|---:|---:|
| Altura do confronto em viewport 1440 px | 4.944 px | 1.300 px |
| Altura do confronto em viewport 390 px | 7.201 px | 1.738 px |
| Acessos de leitura expostos no confronto | 24 linhas | Uma opção principal para a combinação atual; outros períodos recolhidos |
| Topo da identidade da leitura, 1440 px | 834 px | 256 px |
| Topo da identidade da leitura, 390 px | 1.081 px | 364 px |
| Topo da seção do gráfico, 1440 px | 1.396 px | 744 px |
| Topo da seção do gráfico, 390 px | 2.130 px | 1.073 px |

[Antes](evidence/before.json) · [Depois](evidence/layouts.json). Capturas do confronto: [antes desktop](evidence/before-matchup-1440.png), [depois desktop](evidence/matchup-1440-text100.png), [antes mobile](evidence/before-matchup-390.png), [depois mobile](evidence/matchup-390-text100.png). Central: [1440](evidence/calendar-1440-text100.png), [390](evidence/calendar-390-text100.png), [320](evidence/calendar-320-text100.png). Leitura: [1440](evidence/reading-1440-text100.png), [390](evidence/reading-390-text100.png), [320](evidence/reading-320-text100.png).

## Verificação

- **214 testes frontend em 21 arquivos**, incluindo nove novos testes: seleção nominal/dimensões, preservação de referências, associação inclusiva, lacuna, arquivo histórico, contradição, retorno e invariância dos números/descrição acessível do gráfico/detalhes na apresentação guiada. Os cinco `it.fails` legados foram preservados. [Log](checks/tests.log).
- Lint e quatro builds passaram: [lint](checks/lint.log), [percurso](checks/journey-build.log), [real anterior](checks/real-build.log), [experiência sintética](checks/experience-build.log), [público](checks/public-build.log).
- Leitor completo da cópia principal e backup, pins, 48 projeções e **48 respostas HTTP exatamente iguais**; 16 recusas HTTP preservadas. Bundle e cópia de backup não foram modificados. A prova reutiliza o harness anterior, sem o editar. [HTTP](evidence/http.json).
- Navegador: escolha de defesa contra passe, abertura, recarga, retorno e histórico. O recorte BAL exibiu EPA permitido `−0,462`, volume `33`, sucesso `36,4%` (12/33), com o mesmo documento nominal. Lacuna: zero valores e zero barras. Histórico: `archive`, 2025 POST explícito diante do calendário 2026 REG. Agregado: `includes`, dois membros. URL com participante incompatível: zero leituras/valores. [Fluxos](evidence/flows.json).
- Teclado: Tab entre os painéis dos times e controles, foco visível, Espaço selecionando time e defesa. A mudança atualiza a URL e o estado anunciado. [Registro](evidence/keyboard.json).
- **24 combinações**: central/confronto/leitura × 1440/900/390/320 px × fonte raiz 16/32 px, sem overflow horizontal de página. O teste de texto a 200% altera temporariamente a fonte raiz por CDP; não é alegado zoom por atalho nativo. A revisão encontrou e corrigiu 15 px de overflow causados pelo `min-width` herdado de `body` num viewport 320 px com scrollbar. O ajuste está somente no CSS desta entrada. [320 com texto 200%](evidence/matchup-320-text200.png).
- Não foi repetida a inspeção visual de todas as 48 observações nesta rodada. A cobertura de todos os documentos é da prova leitor/HTTP; as verificações visuais cobrem os fluxos e dimensões descritos acima.

## Preservação e limites

O [gate próprio](verify.py) limita as alterações ao percurso, seus novos componentes/testes, opção de apresentação no `Reading` e documentação desta entrega. Matriz de relações, guards das fontes, cliente HTTP/sessão, formatador exato, adaptador, fixtures, fontes, contratos, snapshots, backend, ETL e verificadores anteriores permanecem intactos. JS/CSS públicos mantiveram os mesmos SHA-256 da base estável, conferidos após build. [Resultado](checks/isolation.json).

Arquivo real: bundle `sha256:2fae3be2b1ab7e5799287469ec29b9a98ff652a365ccafcb11b46c55d98ace8a`. Sessão `sha256:a0b4a5b4ffbac39ef3ea827c1c7b0b53a30156aa1a94214da3722630dd3d9e2c`. Completude, cobertura esperada, modelo EPA e conhecimento temporal continuam UNKNOWN. A interface não cria comparação qualificada, previsão de vencedor, ranking ou tese pregame.

A navegação usa os dados disponíveis; vários times continuam com fallback por sigla e diversas partidas não têm leitura individual. O mobile exige rolagem para preservar identidade, controles e contexto; a melhoria não implica que tudo caiba na primeira tela. O relatório não afirma aumento de cliques, retenção ou compreensão: não houve teste com participantes. Aceite visual humano e aceite operacional permanecem pendentes.

[Inicialização e encerramento](README.md). Servidor próprio deixado em loopback, porta 18093, PID 39598 nesta sessão. As versões anteriores não foram encerradas. Dependências locais reaproveitadas, sem instalação de pacotes ou runtime. [Manifesto de evidências](evidence/manifest.json).
