# NFL Sideline · Acabamento textual v3

Base conferida e limpa: `71f46aa4aa456333ff7c5ce26446ec305cdc3d97`. Worktree gerenciada `/Users/pedrocollet/.codex/worktrees/broadcast-copy-polish-v3/NFL Sideline`, branch `codex/broadcast-copy-polish-v3`. A v2 e os servidores anteriores foram preservados. Sem merge, push ou deploy.

[Avaliar o recorte principal](http://127.0.0.1:18088/confronto/dallas-new-england?round=7&period=second&play=rush) · [Pré-jogo](http://127.0.0.1:18088/confronto/green-bay-chicago?round=7) · [Central](http://127.0.0.1:18088/?round=7).

## Três ajustes

| Ponto | Antes | Depois |
| --- | --- | --- |
| Título do segundo tempo, corrida DAL–NE | “NE soma valor; DAL perde.” | “Corrida: EPA positivo para NE, negativo para DAL.” O corpo também nomeia EPA negativo, sem sugerir derrota na partida. |
| Outros títulos | “DAL perde menos valor.”; “Maior EPA, menos sucesso.”; comparação de passe/corrida sem nomear a métrica | “DAL tem EPA menos negativo.”; “Maior EPA, menor frequência de sucesso.”; “Maior EPA” explícito na comparação entre fundamentos. Os ramos de zero também identificam EPA. |
| Legenda de EPA | Explicava os incrementos de escala | “EPA positivo indica ganho de pontos esperados; negativo indica perda. Zero é a referência.” |
| Pré-jogo | Avisos no resumo e bloco inferior com estatísticas, seletores, dados oferecidos e histórico | Um aviso junto à manchete: “Ainda não há estatísticas desta partida.” Bloco inferior removido. Participantes, status, local, kickoff demonstrativo e caminhos para outros jogos preservados. |

Implementação limitada a `editorial.ts`, `Charts.tsx` e `App.tsx`. Nenhum CSS, fixture, teste, limite editorial, critério de decisão, navegação ou cálculo foi alterado. O detalhe da escala continua documentado no README da entrada, no relatório v2 e em `chartScale.ts`: domínio inicial −0,20…+0,40, ampliação em passos de 0,20, intervalo comum e zero explícito.

## Comparações e capturas

| Tela | Desktop 1440 | Mobile 390 | Mobile 320 |
| --- | --- | --- | --- |
| Síntese e legenda | [Antes](evidence/before-slice-1440.png) / [Depois](evidence/after-slice-1440.png) | [Antes](evidence/before-slice-390.png) / [Depois](evidence/after-slice-390.png) | [Antes](evidence/before-slice-320.png) / [Depois](evidence/after-slice-320.png) |
| Pré-jogo | [Antes](evidence/before-pregame-1440.png) / [Depois](evidence/after-pregame-1440.png) | [Antes](evidence/before-pregame-390.png) / [Depois](evidence/after-pregame-390.png) | [Antes](evidence/before-pregame-320.png) / [Depois](evidence/after-pregame-320.png) |
| Divergência EPA/sucesso | [Desktop](evidence/after-divergence-1440.png) | [390](evidence/after-divergence-390.png) | [320](evidence/after-divergence-320.png) |
| Escala ampliada | [Desktop](evidence/after-expanded-scale-1440.png) | [390](evidence/after-expanded-scale-390.png) | [320](evidence/after-expanded-scale-320.png) |

[Detalhe da leitura com os gráficos](evidence/after-reading-detail.png). [Pré-jogo completo com os destinos seguintes](evidence/after-pregame-full-390.png). As capturas das mesas incluem o conteúdo até o fim do painel de análise; o manifesto registra dimensões e hashes.

As fixtures existentes não têm recorte com ambos os EPAs negativos. Para conferir esse ramo no navegador sem alterá-las, montei temporariamente os componentes reais de gráficos e síntese com uma cópia em memória: DAL −0,100, NE −0,200, 20 jogadas por ataque, sucesso 10/20 para ambos. A prévia estava identificada como verificação fora do calendário e foi fechada após a captura: [1440](evidence/controlled-negative-preview-1440.png), [390](evidence/controlled-negative-preview-390.png), [320](evidence/controlled-negative-preview-320.png). Não é um novo confronto navegável nem dado incorporado à experiência.

## Verificação

- Examinei no navegador a v2 antes de editar. Depois conferi os cinco cenários solicitados em 1440, 390 e 320 px. Os novos títulos/legenda quebram naturalmente, sem cortes ou sobreposição; o período e fundamento continuam próximos. [Antes](evidence/before.json), [depois](evidence/after.json), [prévia negativa](evidence/negative-preview.json).
- Comparei **54 recortes das fixtures e oito casos de borda** entre v2/v3, excluindo somente os campos textuais. Decisão, contexto, amostras e apoios são idênticos. Fixtures, escala, navegação, CSS e testes também são idênticos byte a byte. [Prova](evidence/invariance.json); reprodução: `node docs/plans/broadcast-copy-polish-v3/verify-copy.cjs` a partir da raiz desta worktree, com a v2 disponível no caminho informado.
- Pré-jogo: um aviso de ausência, zero placares, gráficos ou seletores da partida; três links para outros jogos da rodada. Identificação persistente mantida. Escala ampliada: KC +0,500 e BUF +0,250, eixo até +0,60, zero em ambas as séries e geometria compatível. [Registro](evidence/browser-checks.json).
- **165 testes existentes em 15 arquivos**, lint, build experimental e build público passaram. Nenhum teste de string foi acrescentado ou expectativa modificada. As cinco falhas esperadas legadas permanecem preservadas. [Testes](evidence/tests.txt), [lint](evidence/lint.txt), [build experimental](evidence/experimental-build.txt), [build público](evidence/public-build.txt).
- Verificação de isolamento herdada passou: paths públicos/protegidos intactos e hashes de JS/CSS públicos idênticos à base estável. Produto público, snapshots, contratos, consumidores, laboratório real, backend e ETL não foram alterados. [Isolamento](evidence/isolation.json). Sem erros de console na página final.

Limitação preexistente observada: no eixo ampliado a 320 px, os rótulos +0,40 e +0,60 se sobrepõem em aproximadamente 6 px. Confirmei coordenadas idênticas na v2 e na v3 ([comparação](evidence/axis-320-comparison.json), [captura v2](evidence/before-expanded-scale-320.png)). Mantive esse comportamento fora dos três ajustes textuais autorizados. Os novos textos não introduzem esse problema.

## Servidor e comandos

Servidor próprio em `127.0.0.1:18088`, PID **4041** nesta sessão. V1 permanece em 18086 e v2 em 18087. A porta da configuração herdada não foi alterada: a v3 usa argumento de linha de comando e mantém `strictPort`. Dependências locais reutilizadas por symlink ignorado.

```bash
cd '/Users/pedrocollet/.codex/worktrees/broadcast-copy-polish-v3/NFL Sideline'
npm --prefix web-ui run experience:dev -- --port 18088
# Encerrar apenas o servidor deixado nesta sessão:
kill -TERM 4041
# Se iniciado no seu terminal, use Ctrl+C naquele terminal.

npm --prefix web-ui test
npm --prefix web-ui run lint
npm --prefix web-ui run experience:build
npm --prefix web-ui run build
python3 docs/plans/broadcast-experience-refinement-v2/verify-isolation.py
```

Entrega encerrada no acabamento textual, com um commit local e worktree limpa. Não houve integração de dados reais, extração de componentes ou reformulação visual.
