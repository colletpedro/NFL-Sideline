# NFL Sideline · Broadcast refinement v2

Entrada experimental independente, sem backend. A rodada 7 reúne quatro confrontos (três encerrados e um pré-jogo), incluindo cobertura parcial de dados. As rodadas 6 e 8 continuam no arquivo. Não integra a entrada pública nem o laboratório real.

```bash
cd '/Users/pedrocollet/.codex/worktrees/broadcast-experience-refinement-v2/NFL Sideline'
npm --prefix web-ui run experience:dev
# http://127.0.0.1:18087/?round=7
```

Porta estrita, host loopback, sem proxy, `publicDir: false`. Se a porta estiver ocupada, o comando falha, sem substituir outro processo. Dependências: as mesmas de `web-ui`; esta worktree reutiliza o `node_modules` local por symlink ignorado. Em um checkout independente: `npm --prefix web-ui ci`.

```bash
npm --prefix web-ui test
npm --prefix web-ui run lint
npm --prefix web-ui run experience:build
npm --prefix web-ui run build
python3 docs/plans/metrics/e5c-3/verify_production.py
python3 docs/plans/broadcast-experience-refinement-v2/verify-isolation.py
```

`fixtures.ts` contém os cenários por tempo e fundamento. Totais, taxas e médias são derivados; um componente ausente invalida o agregado que depende dele. `editorial.ts` transforma o mesmo recorte em uma leitura descritiva e apoios estruturados. Seus limites são específicos da simulação: 10 jogadas por ataque, proximidade de 0,010 EPA/jogada e 2 pontos percentuais de sucesso. Não são critérios estatísticos do produto real.

`state.ts` separa duelo atual, rodada do duelo e origem para retorno. `App.tsx` organiza as páginas; `AnalysisReading.tsx` reúne síntese, tabela e detalhes; `ui.tsx` contém identidades/listas; `Charts.tsx` usa o domínio assinado de `chartScale.ts`. A escala inicial −0,20…+0,40 cresce em passos de 0,20 para acomodar o recorte, sem clipping.

Rotas:

- `/?round=6`, `/?round=7`, `/?round=8`.
- `/confronto/dallas-new-england?round=7`.
- `/confronto/baltimore-dallas?round=6&period=second&play=rush&details=open`.
- `/confronto/new-england-baltimore?round=8`.
- `/confronto/baltimore-pittsburgh?round=7&play=pass` (EPA/sucesso em direções opostas).
- `/confronto/green-bay-chicago?round=7` (pré-jogo, sem placar/estatísticas).
- `/confronto/kansas-city-buffalo?round=7&period=second&play=pass` (ausência e ações para recortes completos).

`round` preserva a seleção da central ao entrar pelo arquivo. O menu da mesa mantém o duelo/recorte atuais. Sem origem explícita, a navegação direta usa a rodada do duelo para retorno. `period`, `play` e `details` mantêm o recorte da mesa; pré-jogo não aplica período/fundamento. Parâmetros inválidos recebem defaults. Os controles não usam armazenamento persistente nem fazem requisições de dados.

O build experimental fica em `web-ui/experience-dist/`, ignorado pelo Git. Sua configuração não é usada pelo build público. Fontes e três escudos permanecem importados do piloto; cinco novos PNGs locais estão em `assets/`, com procedência em `docs/plans/broadcast-experience-refinement-v2/assets.json`. O relatório e as capturas ficam em `docs/plans/broadcast-experience-refinement-v2/REPORT.md`.
