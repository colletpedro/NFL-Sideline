# NFL Sideline · Broadcast experience v1

Entrada experimental independente. Três duelos fictícios, central editorial e mesa de análise, sem backend. Não integra a entrada pública nem o laboratório anterior.

```bash
cd '/Users/pedrocollet/.codex/worktrees/broadcast-experience-v1/NFL Sideline'
npm --prefix web-ui run experience:dev
# http://127.0.0.1:18086/?round=7
```

Porta estrita, host loopback, sem proxy, `publicDir: false`. Se a porta estiver ocupada, o comando falha, sem substituir outro processo. Dependências: as mesmas de `web-ui`; esta worktree reutiliza o `node_modules` local por symlink ignorado. Em um checkout independente: `npm --prefix web-ui ci`.

```bash
npm --prefix web-ui test
npm --prefix web-ui run lint
npm --prefix web-ui run experience:build
npm --prefix web-ui run build
python3 docs/plans/metrics/e5c-3/verify_production.py
python3 docs/plans/broadcast-experience-v1/verify-isolation.py
```

`fixtures.ts` contém os cenários por tempo e fundamento. Totais, taxas e médias são derivados. `state.ts` interpreta o estado compartilhável na URL; `App.tsx` organiza as páginas, `ui.tsx` as identidades/listas, `Charts.tsx` as visualizações. As fontes e os três escudos são importados dos arquivos locais preservados do piloto.

Rotas:

- `/?round=6`, `/?round=7`, `/?round=8`.
- `/confronto/dallas-new-england?round=7`.
- `/confronto/baltimore-dallas?round=6&period=second&play=rush&details=open`.
- `/confronto/new-england-baltimore?round=8`.

`round` preserva a seleção da central, mesmo ao entrar em um duelo de outra rodada pelo arquivo. `period`, `play` e `details` mantêm o recorte da mesa. Parâmetros inválidos recebem defaults; confrontos desconhecidos têm uma saída para a central. Os controles não usam armazenamento persistente nem fazem requisições de dados.

O build experimental fica em `web-ui/experience-dist/`, ignorado pelo Git. Sua configuração não é usada pelo build público. O relatório e as capturas estão em `docs/plans/broadcast-experience-v1/REPORT.md`.
