# Nova sessão: escolher o primeiro modelo

O usuário considera a interface concluída e aprovada. A última rodada automática está documentada neste diretório. A próxima sessão deve começar pelas **perguntas de produto e pesquisa do primeiro modelo**, e não por outra reformulação visual ou pela implementação de vários modelos.

## Ponto de partida verificável

- Repositório principal: `/Users/pedrocollet/Downloads/NFL Sideline`.
- Checkout com a experiência aprovada: `/Users/pedrocollet/.codex/worktrees/broadcast-score-curve-v2/NFL Sideline`.
- Branch: `codex/broadcast-score-curve-v2`.
- Commit de código após a auditoria: **`7a70e60e9710c838a5a612aeb80b71e3cd6550ee`**. O fechamento documental pode aparecer em um commit posterior na mesma branch; conferir HEAD/status antes de trabalhar.
- Site: `http://127.0.0.1:18111/?season=2026&week=7`.
- Inicialização: `docs/plans/broadcast-score-curve-v2/run-local.sh` na raiz desse checkout. Servidor conferido na auditoria: PID 83042; não confiar no PID após reinício, conferir a porta.
- Não houve merge, push ou deploy. O produto público ainda tem seus contratos/snapshots próprios e não deve ser sobrescrito pelo experimento.

A auditoria abriu as 146 páginas principais em desktop, mobile e fonte ampliada. A única correção de comportamento necessária foi alinhar sugestões da busca ao escopo semanal; também foi corrigido o singular das contagens. Não restou bloqueio funcional nos cenários executados. Foram 370 testes frontend e 714 Python distintos aprovados, além de builds, isolamento e reconciliação. Leia `README.md` para cobertura e limites, sem converter a automação em evidência de compreensão humana.

## Dados existentes

Pacote durável:

`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-score-curve-v2/20261027-v1/bundle`

Pins preservados:

- Curva/eventos: `sha256:86fd64d2e3ac628cf8a99ca1befe95d4528e8cf7acba1f4937235fe9fb3f7ecd`.
- Cronologia: `sha256:93b6cad3ea3a1db822c16e4bfdadf70f28122e2dd60002708d44745776129624`.
- Coleção W1–7: `sha256:77af196874e984bfa85a270da8733073f97836e959b6dd3d2cd2ec8a98bc7a0c`.

A coleção está em `bundle/source/source/`; o PBP congelado em `bundle/source/source/source/pbp.parquet`. O pacote contém a cadeia de fontes e manifests; use os leitores/validadores existentes e os recibos, sem editar artefatos pinados. Há cópias de recuperação documentadas no plano `broadcast-score-curve-v2`.

Cobertura: 2026 REG, W1–7, 107 jogos, 32 times, 18.738 linhas PBP na fonte congelada em 27/10/2026. Disponíveis: EPA geral/passe/corrida, terceiras, red zone por campanha, EPA de jogadas que começam na red zone, cronologia e agregados reais. Modelo EPA, completude, cobertura esperada e disponibilidade histórica continuam UNKNOWN. Não promover essas garantias por causa da auditoria de interface.

## Intenção do usuário

Ele quer transformar o projeto, gradualmente, em um hub de modelos. Já citou interesses em quarterbacks, situações de fim de jogo, pressão e distinção entre interceptações e qualidade da decisão. **Não quer implementar todos agora.** A etapa de análises situacionais veio primeiro e está estabelecida.

Na nova sessão:

1. Escolher com ele uma pergunta concreta, a unidade de análise, o alvo e o uso pretendido: descrição, estimativa ou previsão.
2. Conferir quais variáveis realmente existem e suas definições. Não chamar `qb_hit` de toda pressão, nem inferir “passe interceptável” só pelo desfecho observado; verificar se há rótulo adequado antes de prometer esses casos.
3. Definir quais informações poderiam ser conhecidas no momento da previsão, evitando usar resultado da jogada, placar futuro, agregados inclusivos futuros ou outra informação posterior como feature.
4. Inventariar a história necessária. W1–7 sustenta a experiência exploratória, mas a quantidade de dados para treinar e avaliar dependerá da pergunta. Se forem necessárias temporadas anteriores, planejar a aquisição compatível com o ETL e suas fontes; não usar o conjunto de teste para ajustar o modelo.
5. Propor uma baseline simples e uma avaliação temporal apropriada, com métricas ligadas ao objetivo. Depois avançar para **um modelo por vez**.

Essas decisões fazem parte do início do primeiro modelo, não de outra entrega obrigatória de acabamento visual. Preserve a identidade ardósia/cores dos times/Archivo + Roboto Condensed e o percurso hub → confronto → time. Leia AGENTS.md, Spec.md, contrato público e estado local antes de alterações. A coleta humana anterior foi encerrada pelo usuário em P01/N=1; não exigir novos participantes para iniciar esta fase.
