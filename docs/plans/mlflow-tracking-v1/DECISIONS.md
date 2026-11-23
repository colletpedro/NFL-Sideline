# Registro de decisões

Cada decisão tem data, quem decidiu e se está aberta à revisão. Decisões tomadas por padrão (marcadas
"padrão do orquestrador") podem ser revertidas pelo dono do projeto a qualquer momento; o custo de reverter está
anotado.

| # | Data | Decisão | Quem | Estado | Custo de reverter |
|---|---|---|---|---|---|
| D1 | 23/11/2026 | Trabalhar no branch novo `codex/mlflow-tracking-v1` a partir de `ed2a008` (ponta da cadeia `qb-*`), numa worktree em `.claude/worktrees/mlflow-tracking-v1` | Padrão do orquestrador (recomendação aceita no pedido) | Revisável | Rebase do branch sobre outra base |
| D2 | 23/11/2026 | Importar os três experimentos, começando pela v1 para validar o importador | Padrão do orquestrador | Revisável | Remover experimentos no MLflow |
| D3 | 23/11/2026 | A Fase 5 pode alterar o laboratório de desfechos (`risk-outcomes/Lab.tsx` e fronteira Vite), só para ler a proveniência | Padrão do orquestrador; previsto no plano | **Confirmar com o dono antes do merge** | Reverter arquivos do `web-ui` da Fase 5 |
| D4 | 23/11/2026 | Adicionar ao `.gitignore` o store do MLflow e os stores `qb-*` na Fase 1, em bloco separado | Padrão do orquestrador | Revisável | Remover as linhas |
| D5 | 23/11/2026 | MLflow como índice alimentado por importador só leitura, sem instrumentar código congelado | Fase 0 | Aceita no plano | Alto (exigiria descongelar código) |
| D6 | 23/11/2026 | `mlflow==3.17.2` (21/10/2026, último patch da 3.17; 3.18.0 tem 20 dias) | Orquestrador | Revisável | Trocar a versão no lock e reimportar |
| D7 | 23/11/2026 | Modelos registrados como pyfunc *models from code*; artefato = JSON congelado; inferência reaproveitada por import quando possível, senão reimplementação mínima com teste de igualdade contra o original | Orquestrador | Revisável | Reregistrar |
| D8 | 23/11/2026 | Proveniência versionada em `docs/plans/mlflow-tracking-v1/provenance.json` (o plano anterior citava `docs/plans/mlflow/`) | Orquestrador | Revisável | Mover o arquivo |
| D8a | 23/11/2026 | D8 revista: o arquivo de proveniência passa a `web-ui/broadcast-journey/risk-outcomes/provenance.json`, versionado e importado pelo laboratório na build; o servidor Vite do laboratório só permite ler arquivos dentro de `web-ui/`, e a config Vite não está entre os arquivos autorizados | Orquestrador | Revisável | Mover o arquivo e ajustar o import |
| D11 | 23/11/2026 | O home real do MLflow foi reconstruído do zero após o endurecimento; o anterior foi movido para o scratchpad da sessão (não apagado). Rebuilds geram `run_id` novos, então a proveniência muda de `run_id` quando o home é reconstruído, mesmo com o mesmo modelo | Orquestrador | Aceita | — |
| D12 | 23/11/2026 | `npm ci` permitido em `W/web-ui` com Node 24 para rodar os testes da Fase 5 | Orquestrador | Revisável | Apagar `node_modules` |
| D9 | 23/11/2026 | Agentes: implementador e revisor em Sonnet; batedor e verificador em Haiku; orquestração e verificação final pelo modelo principal | Pedido do dono | Aceita | — |
| D10 | 23/11/2026 | Nenhum commit é feito pelos agentes nem pelo orquestrador; o dono revisa e commita | Regra da sessão | Aceita | — |

## Perguntas abertas

- D3 precisa de confirmação explícita antes de qualquer merge.
- ADR-011 está como "proposto"; aceitar ou ajustar é decisão do dono.
