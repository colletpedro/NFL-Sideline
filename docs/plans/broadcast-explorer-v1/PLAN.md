# NFL Sideline · Explorador de recortes v1

Plano registrado antes da implementação. Base exata: 5348ab117bffd01c75323a0c56466e450b522260, referência copy-v2 em 18099 preservada. Experimento reversível local; sem promoção, merge, push ou deploy.

Hipótese: uma resposta inicial identificada e três perguntas concretas permitem investigar sem reconstruir time, perspectiva e período. Não se presume melhoria de compreensão ou esforço humano.

## Entrada e estado

Decisão: `/?view=explorer` na entrada broadcast-journey, reutilizando calendário, transportes e documentos. Nenhuma entrada pública é alterada. URLs sem esse modo continuam anteriores. Links explícitos de entrada e retorno. O estado usa as dimensões existentes (season/week/game/team/side/reading/analysis), `question=distance|type|outcomes`, `refine` e até dois `pin` nominais contendo documento, pergunta, refinamento e pin da fonte. Sem números livres nem escolha de transporte em URL. Contexto novo: exemplo NYJ/ataque/W1, rotulado e materializado na URL. Contexto explícito inválido não é substituído. Origem de calendário/busca conservada por cópia dos parâmetros.

## Composição e interação

Cenário ardósia #24333e/#304958, painel claro #edf1f2, texto #17232c/#405866, acento #d9ec91; Archivo e Roboto Condensed e logos existentes. Um painel contínuo: contexto compacto editável, três perguntas, resultado com regra, gráfico com refinamento local, aprofundamento e método copy-v2. Não repetir filtros por análise. Perspectiva e período com alteração direta; jogo/time disponíveis sob troca de contexto. A seleção não dispara foco/scroll a cada alteração.

Distância e tipo são marginais separadas: perguntas distintas e refinamento único por pergunta; nunca distância × tipo. Red zone destaca desfecho sobre todas as campanhas, mantendo taxa geral de TD e denominador. Projeção de tela separada e identificada; DTO original intacto, usado no método. Fonte insuficiente bloqueia taxas, zero denominador permanece sem taxa.

Fixar: dois recortes no máximo, identidades da fonte em URL e reidratação no snapshot validado. Cada item conserva time/lado, jogos/adversários, período, pergunta/refinamento, unidade/razão/versões. Trocar a investigação não muda itens. Remover/substituir explícitos. Comparação descritiva com aviso de incompatibilidade e sobreposição; nenhuma diferença entre métricas incompatíveis.

## Verificação prevista

Testes de estado/URL, projeções/imutabilidade, marginais, denominadores, comparações e dados reais; frontend completo com cinco expected-failure intactos, lint e quatro builds. HTTP igual à referência para ambos os transportes e pin privado. Build público JS/CSS byte a byte. Navegador nas seis tarefas equivalentes, 1440/390/320 e texto200%, teclado/foco/histórico/recarga, capturas e correções após inspeção.

## Orientações consultadas somente em leitura

Impeccable não instalado. [Skill oficial](https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/SKILL.md), [distill](https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/reference/distill.md), [operate](https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/reference/operate.md), [craft floor](https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/reference/craft-floor.md), consultados em 23/10/2026 via Firecrawl. Nenhum script, instalador ou ferramenta do projeto externo executado. Aplicação: consolidar controles, eliminar cartões/repetições, manter contexto e resultados próximos; briefing de identidade prevalece sobre sugestões gerais de tipografia/paleta.
