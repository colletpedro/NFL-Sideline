# NFL Sideline · Percurso guiado v2

[Explorar a central](http://127.0.0.1:18093/?season=2026&week=1&filter=participants) · [Escolher leitura de BAL–IND](http://127.0.0.1:18093/?season=2026&week=1&filter=participants&game=2026_01_BAL_IND) · [Lacuna BAL–DAL](http://127.0.0.1:18093/?season=2026&week=3&filter=participants&game=2026_03_BAL_DAL) · [Arquivo histórico de NE](http://127.0.0.1:18093/?season=2026&week=3&filter=participants&game=2026_03_NE_JAX).

O time é selecionado no próprio painel de identidade. Ataque/defesa e fundamento determinam a opção de leitura; abrir a observação exige uma ação explícita. Períodos mais amplos e arquivos históricos ficam recolhidos, com seu vínculo identificado. A central não repete o destaque na lista.

[Relatório e comparações](REPORT.md) · [Plano](PLAN.md) · [24 verificações de layout](evidence/layouts.json) · [Prova HTTP/leitor](evidence/http.json) · [Preservação](checks/isolation.json).

## Operação local

Worktree: `/Users/pedrocollet/.codex/worktrees/broadcast-journey-polish-v2/NFL Sideline`. Branch `codex/broadcast-journey-polish-v2`. Base exata `46e2252476738c8240a26b38242e66ca20a75d42`.

Servidor próprio deixado em `127.0.0.1:18093`, PID `39598` nesta sessão. As versões anteriores continuam independentes. A configuração herdada não teve sua porta padrão alterada; esta execução usa variável explícita.

```bash
cd '/Users/pedrocollet/.codex/worktrees/broadcast-journey-polish-v2/NFL Sideline'
export NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
export NFL_OBSERVATION_CONFIG='/Users/pedrocollet/Downloads/NFL Sideline/docs/plans/metrics/e5c-3r/lab-config.json'
export NFL_LOCAL_JOURNEY_PORT=18093
PATH=/opt/homebrew/opt/node@24/bin:$PATH npm --prefix web-ui run journey:dev
# Se iniciado no seu terminal, encerre com Ctrl+C naquele terminal.
# Para encerrar somente o servidor deixado nesta sessão:
kill -TERM 39598
```

A porta deve estar livre para uma nova execução; não encerre servidores de outras versões. O bundle deve existir nos caminhos preservados da recuperação E5c-3R. Não há substituição por fixture sintética.

## Verificações reproduzíveis

Dependências locais já existentes são reutilizadas por symlink ignorado; nenhum pacote ou runtime foi baixado.

```bash
npm --prefix web-ui test
npm --prefix web-ui run lint
npm --prefix web-ui run journey:build
npm --prefix web-ui run real:build
npm --prefix web-ui run experience:build
npm --prefix web-ui run build
python3 -B docs/plans/broadcast-journey-polish-v2/verify.py
# Com o servidor ativo; use um output novo para sua execução:
"$NFL_OBSERVATION_PYTHON" -B docs/plans/broadcast-real-observation-v1/proof.py \
  --config "$NFL_OBSERVATION_CONFIG" --port 18093 \
  --output /private/tmp/nfl-journey-polish-v2-recheck.json
git diff --check 46e2252476738c8240a26b38242e66ca20a75d42
```

A leitura do gate confere as evidências registradas e a preservação atual; não substitui uma nova inspeção no navegador. O padrão da central continua sendo definido pela publicação e pela data UTC. Os links acima escolhem explicitamente a semana 1 para facilitar a avaliação de jogos com observação individual.
