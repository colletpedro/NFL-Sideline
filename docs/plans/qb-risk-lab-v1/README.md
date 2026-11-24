# Laboratório — risco de passe · v1

Versão local navegável, sem publicação externa. Base: pesquisa v2 `a6d3672f770e7d5db3728edbff216b229fc6aba7`; worktree gerenciada separada `codex/qb-risk-lab-v1`. A [decisão de 04/11](DECISION.md) substitui a espera da reserva antiga. Fontes/protocolos v1/v2 permanecem intactos; isto é exploração contínua.

Abra **http://127.0.0.1:18121/?view=risk-lab&season=2026**. Há entrada no cabeçalho do hub, dos confrontos e dos times da cópia da experiência aprovada. O acervo esportivo anterior continua W1–7; só o laboratório usa a cobertura nova W1–8.

Exemplos de navegação:

- [Daniel Jones, acumulado](http://127.0.0.1:18121/?view=risk-lab&season=2026&player=00-0035710):267 passes, 8 jogos, 17 rótulos, 8,66 esperados; não é diagnóstico de qualidade.
- [Matthew Stafford](http://127.0.0.1:18121/?view=risk-lab&season=2026&player=00-0026498): identidade/equipe e cálculo próprio.
- [Evidência W8: não interceptável e interceptado](http://127.0.0.1:18121/?view=risk-lab&season=2026&player=00-0035710&period=8&cross=01&play=2026_08_IND_JAX%3A2125).
- [Todos os lançadores/volumes](http://127.0.0.1:18121/?view=risk-lab&season=2026&position=all&volume=all), inclusive outras posições.

## Operação local

Todos os comandos partem desta worktree:
`/Users/pedrocollet/.codex/worktrees/qb-risk-lab-v1/NFL Sideline`.

O ambiente Python fica em `research/qb_risk_lab/.venv`, fora do Git. Recriação offline no mesmo macOS/arquitetura/Python 3.11:

```sh
python3.11 -m venv research/qb_risk_lab/.venv
research/qb_risk_lab/.venv/bin/python -m pip install --no-index --find-links '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-lab-v1/recovery/20261104-v1/wheelhouse' -r research/qb_risk_lab/requirements.lock
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui ci
docs/plans/qb-risk-lab-v1/run-local.sh
```

`npm ci` precisa do cache/registro npm; a reprodução offline de dados/modelo usa os wheels congelados. O build arquivado também pode ser servido sem npm, apenas com Node. Não carregamos `.env`, banco, Gemini ou pickle. O script do site usa os leitores aprovados e o Python ETL **somente para leitura local**, sem instalar nada no ambiente compartilhado.

Porta 18121, host 127.0.0.1, `strictPort`; conflito encerra a tentativa, sem buscar outra porta e sem matar ninguém. O processo deixado nesta entrega é documentado no [HANDOFF](HANDOFF.md). Ao reiniciar, conferir PID/porta novamente. Parar apenas o próprio processo: Ctrl-C no terminal; ou verificar `lsof -nP -iTCP:18121 -sTCP:LISTEN` e então enviar SIGTERM ao PID conferido. O servidor aprovado 18111 não foi reiniciado nem encerrado.

## Atualização manual

```sh
docs/plans/qb-risk-lab-v1/update.sh
```

Este único comando adquirePBP/FTN/calendário/roster 2026→valida→aplicaM3 congelado→gera pacote imutável→escreve revisão/recibo→substitui atomicamente `current.json`. O destino padrão é:

`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-lab-v1`.

Pode ser alterado por `NFL_RISK_LAB_STORE`, também na execução do servidor. Destinos nos checkouts e stores protegidos v1/v2/broadcast são recusados. `runs/<UTC>/sources.json` registraURLs, horários, tamanhos, hashes/licenças; `audit.json` traz o funil por jogo; `revision.json`lista inclusões/remoções/alterações por passe e `labelChanges`; `receipt.json` registra ativação ou ausência de mudança. Falhas deixam `failure.json` e a versão ativa anterior. `.updating` impede concorrência; se um processo for morto à força, conferir ausência de atualização antes de remover manualmente o lock abandonado. Não há rotina recorrente.

O servidor lê o ponteiro a cada pedido do índice. Use “Conferir versão disponível” ou recarregue para receber uma atualização. Detalhes são pedidos pelo ID imutável do pacote exibido, evitando misturar temporadas/versões. “Conferir” não baixa dados nem muda o modelo.

Ausência em um jogo exclui **todo aquele jogo**, com motivo visível; os demais podem entrar, mesmo em semana parcial. Duplicidade, tipos incompatíveis, identidade/calendário contraditórios, placar incoerente, hash/modelo inválido bloqueiam a ativação. A fonte pode sofrer revisões futuras. Join completo e marcador final não certificam que o charting é verdadeiro ou imutável.

## Reprodução offline em destino novo

```sh
docs/plans/qb-risk-lab-v1/reproduce.sh '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-lab-v1/reproduction/minha-revisao-nova'
```

Recusa destino existente. Cria outrovenv, verifica fontes, reaplicaM3, reconcilia todas as chaves viaSQL independente e compara **todos os arquivos do pacote** com a cópia congelada. O recibo fica em `<destino>/reproduction.json`. Não toca o ponteiro ativo. O local já executado está em [evidence/reproduction.json](evidence/reproduction.json); não reutilizar esse destino sem escolher nova pasta.

A aquisição inicial pinada está em `runs/20261104T144706530236Z/`. Repetir só essa aquisição, sem rede:

```sh
docs/plans/qb-risk-lab-v1/update.sh --sources '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-lab-v1/recovery/20261104-v1/sources'
```

A semântica igual mantém o mesmo pacote; timestamps de recibos/diretórios não precisam ser idênticos. A igualdade de bytes observada vale para este ambiente/fontes/modelo congelados; em outro ambiente, conferir recibo e tolerâncias numéricas, sem prometer igualdade universal.

## Build preparado para revisão de publicação

```sh
docs/plans/qb-risk-lab-v1/build-local.sh
PATH=/opt/homebrew/opt/node@24/bin:$PATH node web-ui/scripts/risk-lab-built.mjs
```

Build separado em `web-ui/risk-lab-dist`,209 documentosGETcongelados, fontes/logos locais. Preview em 127.0.0.1:18122, sem fallback de porta. `local-routes.json` contémURLs, hashes e headers necessários ao acervo aprovado; o preview verifica hashes. Posterior hospedagem precisa mapear esses endpoints/headers e SPA; **não** basta substituir `web-ui/dist` nem copiar snapshots para `public/data`. Nenhuma configuração Vercel pública foi alterada. Não houve deploy/publicação nem promessa de direitos irrestritos: ver atribuição/ShareAlike no [relatório](REPORT.md).

Após uma nova atualização, executar novamente o build para renovar a cópia estática. O servidor 18121 usa o pacote ativo dinamicamente; 18122 é uma fotografia do build.

## Testes e evidências

```sh
research/qb_risk_lab/.venv/bin/python -m pytest research/qb_risk_lab/test_pipeline.py research/qb_interception_risk/tests research/qb_risk_temporal_v2/tests -q
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui test
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run lint
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run build
research/qb_risk_lab/.venv/bin/python research/qb_risk_lab/check_isolation.py
```

[Dados e cobertura](DATA-COVERAGE.md) · [Relatório](REPORT.md) · [Verificação/capturas](VERIFICATION.md) · [Passagem técnica](HANDOFF.md). Os cinco `it.fails` legados continuam intactos; os skips preexistentes não são anunciados como testes executados.

Encerramento direcionado e conferido por comando/cwd:

```sh
docs/plans/qb-risk-lab-v1/stop-local.sh
```

Para gerar outra cópia de recuperação, use `research/qb_risk_lab/archive.py --help`,escolhendo destinos novos. O script recusa sobrescrita e verifica todos os membros do tar por hash. A cópia de 04/11 está em [evidence/recovery.json](evidence/recovery.json).
