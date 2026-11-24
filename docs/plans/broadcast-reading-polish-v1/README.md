# Acabamento de leitura v1

Base conferida: `cb4e2cd181fdca5c2b0c11ff38c6c3ea20df6ad4`, branch `codex/broadcast-hub-team-w12-v1`, árvore limpa. Referência 18105 preservada. Feedback direto do usuário; não constitui nova sessão humana nem estudo de sucesso.

## Plano anterior à implementação

1. Ativar a apresentação somente na entrada própria 18106, mantendo entradas e comportamento anteriores como padrão. Reutilizar hub, páginas, builders de URL, leitores e snapshot validado.
2. Uma identidade = um link contendo logo, sigla sublinhada e nome, fora do placar. Aplicar ao confronto e às três densidades de jogos, inclusive componentes do time.
3. Compartilhar o símbolo final entre quatro exemplos de legenda e todas as tentativas. Círculo/passe, quadrado/corrida; grafite preenchido/check para conversão, contorno/traço para não conversão. Foco/seleção independentes do resultado. Remover cor de equipe dessa apresentação.
4. Substituir pontos empilhados por linhas identificadas: logo original sobre painel claro, sigla, posição exata no domínio 0–100%, percentual e razão. Ordenar razões por multiplicação cruzada exata e desempatar por sigla; nenhum ranking de qualidade. Inventário sem taxa fica fora da escala.
5. Nas terceiras/red zone, percentual será o resultado principal, com razão imediatamente ao lado. Painel contínuo, divisória e plano discreto da categoria dão profundidade sem cobrir dados. Estados sem taxa mantêm texto próprio.
6. Destaque terá palco de logos, duas identidades e placar central, enquanto apoios/compactos permanecem itens horizontais. No mobile, compor três colunas e nomes abaixo das logos, em vez de alongar o cartão comum.

Tokens preservados: ardósia, papel azul-claro `#D6E1E6`, tinta `#15232C`, cores dos times nas identidades; Archivo na leitura e Roboto Condensed nos resultados. Conversões usarão grafite comum. Sem novos ativos, fontes, dependências, animação ou controles analíticos.

## Fonte e isolamento

Pacote imutável: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle`.
Pin `sha256:8971d767b6ec0557465aeb65aeb00533fd10255a62f4b916954b3854daa15cef`.
Coleção incorporada `source/matchups`: `sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc`.
Nada será regenerado. A prova de preservação comparará respostas HTTP integrais e unidades, além dos hashes públicos. Nenhum Python, contrato ou fonte será alterado.

## Inspeção anterior

NE × SEA: “NEVer time” visualmente unido; falhas NE vermelhas e SEA azuis; exemplos da legenda não reproduzem os símbolos preenchidos reais; 32 pontos exigem interação para saber os times; razão tem mais destaque que percentual. No hub 390 px, destaque e apoios repetem a mesma divisão vertical. Capturas em `captures/before-*`.

## Verificação planejada

Pacotes reais, testes de apresentação e consumidores anteriores, lint/TypeScript/builds afetados e público. Conferência de dados por HTTP sem repetir geração histórica. Navegador em 1440, 390, 320, texto 200%, foco/teclado, NE × SEA, NYJ × TEN, ATL, página do time e retorno com consulta/semana. Registrar ajustes após inspeção e pendências reais em REPORT.md.


## Operação

Instância própria: `http://127.0.0.1:18106/`. PID observado: **25458**. Encerramento direcionado: `kill -TERM 25458` (confira o PID/listener antes de usar no futuro). Servidores 18098–18105 preservados, especialmente referência 18105/PID 59966.

```sh
cd "/Users/pedrocollet/.codex/worktrees/broadcast-reading-polish-v1/NFL Sideline"
sh docs/plans/broadcast-reading-polish-v1/run-local.sh
# Verificar o listener próprio
lsof -nP -iTCP:18106 -sTCP:LISTEN
# Contraprova sem regeneração
python3 docs/plans/broadcast-reading-polish-v1/check-http.py
python3 docs/plans/broadcast-reading-polish-v1/check-builds.py
python3 docs/plans/broadcast-reading-polish-v1/verify-isolation.py
```

O startup mantém configurações explícitas do operador para os pacotes duráveis existentes; `NFL_TEAM_CONFIG` e `NFL_W12_CONFIG` admitem configuração local do operador, nunca URL/browser. Todos os cinco readers usam 18106. Não alterar manualmente só a porta de um deles. Cache Vite exclusivo sob `node_modules/.vite-broadcast-reading-polish-v1`. A build privada fica em `web-ui/reading-polish-dist`, sem cópia de artefatos para public/data.

Links: [hub W1](http://127.0.0.1:18106/?season=2026&week=1), [hub W2](http://127.0.0.1:18106/?season=2026&week=2), [NE × SEA](http://127.0.0.1:18106/?view=matchup-w12&game=2026_01_NE_SEA), [NYJ × TEN](http://127.0.0.1:18106/?view=matchup-w12&game=2026_01_NYJ_TEN), [time NYJ](http://127.0.0.1:18106/?view=team-w12&team=NYJ&season=2026&returnWeek=1), [ATL sem oportunidades](http://127.0.0.1:18106/?view=team-w12&team=ATL&season=2026&returnWeek=2#team-redzone), [referência preservada](http://127.0.0.1:18105/?season=2026&week=1).

[Relatório, antes/depois e limites](REPORT.md). Branch `codex/broadcast-reading-polish-v1`; commits locais e HEAD final verificáveis por `git log -3 --oneline` e informados no fechamento. Sem promoção automática.

Para reproduzir os testes com fontes reais habilitadas (sem credenciais):

```sh
export NFL_TEAM_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-hub-team-w12-v1/20261024-v1/bundle'
export NFL_W12_QA_BUNDLE="$NFL_TEAM_QA_BUNDLE/source/matchups"
export NFL_MATCHUP_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled'
export NFL_SITUATIONAL_QA_BUNDLE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-situational-w12-v1/20261023-v1/bundle-reconciled'
export PATH="/opt/homebrew/opt/node@24/bin:$PATH"
npm --prefix web-ui test
PYTHONPATH="$PWD/etl-pipeline/src" '/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' -m pytest -q etl-pipeline/tests/test_team_w12.py -k 'real_package_reader_integrity or zero_opportunities or unavailable_component or missing_component'
```

As oito builds e configurações TypeScript/lint são enumeradas e têm seus logs em `checks/builds.json`; o script `check-builds.py` encerra no primeiro erro e confere os hashes públicos. A verificação de isolamento espera os listeners desta sessão; PIDs precisam ser reconferidos quando uma instância for reiniciada.
