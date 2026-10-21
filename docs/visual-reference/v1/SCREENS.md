# Telas adotadas e reprodução

As imagens deste pacote foram capturadas no navegador sobre o commit de implementação `840e3603920b3db15dca44116d2072f5a8528d4f`, sem alterar fixtures, estilos ou textos. São capturas de página inteira, com viewport inicial de altura 1000 px, densidade 1, fonte raiz padrão de 16 px e sem zoom. A altura de cada PNG é a do conteúdo completo. Rotas, dimensões, bytes e SHA-256 estão no [manifesto](manifest.json).

| Tela | Rota | Capturas (dimensões do PNG) |
| --- | --- | --- |
| Central, quatro jogos | `/?round=7` | [1440×1691](images/home-1440.png) · [390×2574](images/home-390.png) |
| Confronto, segundo tempo/corrida | `/confronto/dallas-new-england?round=7&period=second&play=rush` | [1440×2637](images/matchup-1440.png) · [390×3948](images/matchup-390.png) |
| Pré-jogo | `/confronto/green-bay-chicago?round=7` | [1440×1397](images/pregame-1440.png) · [390×1942](images/pregame-390.png) |
| Ausência e domínio negativo | `/confronto/kansas-city-buffalo?round=7&period=second&play=pass` | [1440×2627](images/missing-1440.png) · [390×3979](images/missing-390.png) |
| Eixo ampliado corrigido | `/confronto/kansas-city-buffalo?round=7&period=first&play=pass` | [320×4076](images/axis-expanded-320.png) |

```bash
cd '/Users/pedrocollet/.codex/worktrees/broadcast-axis-baseline-v4/NFL Sideline'
npm --prefix web-ui run experience:dev -- --port 18089
```

Abra `http://127.0.0.1:18089` seguido da rota. Ajuste o viewport à largura da captura, altura 1000 px e densidade 1; aguarde as fontes locais e capture a página inteira a partir do topo. O manifesto identifica o estado, sem depender de armazenamento persistente. `details=open` abre as contagens equivalentes; por exemplo, acrescente `&details=open` ao confronto com eixo ampliado.

Host loopback e porta estrita, sem proxy ou backend. A configuração herdada permanece intacta: a porta própria é passada no comando. Dependências existentes são reutilizadas por symlink ignorado; em checkout independente use `npm --prefix web-ui ci`. O build experimental sai em `web-ui/experience-dist/`, ignorado no Git.

Servidor deixado nesta sessão: PID **15045**. Para encerrar apenas esse processo: `kill -TERM 15045`. Se iniciado no seu terminal, use Ctrl+C naquele terminal. Os servidores de v1/v2/v3 permanecem em 18086/18087/18088.

Validações reproduzíveis:

```bash
npm --prefix web-ui test
npm --prefix web-ui run lint
npm --prefix web-ui run experience:build
npm --prefix web-ui run build
python3 docs/plans/broadcast-experience-refinement-v2/verify-isolation.py
```

A comparação antes/depois do eixo e as medições das larguras 320/390/1024/1440 e do texto ampliado estão no [relatório técnico da v4](../../plans/broadcast-axis-baseline-v4/REPORT.md).
