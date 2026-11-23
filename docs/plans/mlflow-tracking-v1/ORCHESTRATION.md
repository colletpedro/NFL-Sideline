# Orquestração com agentes

Os agentes ficam em [`.claude/agents/`](../../../.claude/agents/). Todos leem [GUARDRAILS.md](GUARDRAILS.md)
antes de agir.

| Agente | Modelo | Ferramentas | Quando usar |
|---|---|---|---|
| `mlflow-scout` | Haiku | leitura + escrita só do arquivo de saída | Levantar esquemas e valores reais dos stores antes de implementar; tarefas de leitura volumosas e mecânicas |
| `mlflow-implementer` | Sonnet | leitura, escrita, Bash | Escrever ou corrigir código e testes que exigem julgamento |
| `mlflow-verifier` | Haiku | leitura, Bash | Rodar os critérios de "pronto quando" e as checagens de proteção; devolver saídas literais |
| `mlflow-reviewer` | Sonnet | leitura, Bash | Revisão adversarial de correção antes de fechar uma fase |

## Ciclo por fase

1. **Fatos** — um ou mais `mlflow-scout` em paralelo escrevem `facts-*.md` no scratchpad da sessão. Fatos
   estáveis e úteis para as próximas fases são copiados para `docs/plans/mlflow-tracking-v1/facts/`.
2. **Implementação** — um `mlflow-implementer` por conjunto de arquivos (nunca dois escrevendo os mesmos
   arquivos ao mesmo tempo), com briefing que cita a seção do PLAN, os fatos e os arquivos autorizados.
3. **Verificação** — `mlflow-verifier` roda os testes, o critério da fase e as proteções.
4. **Revisão** — `mlflow-reviewer` procura defeitos com prova executada. Achados voltam ao implementador.
5. **Fechamento** — o orquestrador confere pessoalmente o critério da fase, registra em
   [CHECKPOINTS.md](CHECKPOINTS.md) e decide a próxima fase. Qualquer coisa que dependa de opinião do dono vai
   para [DECISIONS.md](DECISIONS.md) e interrompe o fluxo.

## Escolha de modelo

- Haiku: leitura e descrição de arquivos, execução de comandos com resultado verificável, checagens repetitivas.
- Sonnet: código novo, correção de bugs, revisão, qualquer tarefa em que um erro silencioso custaria caro.
- Modelo principal (orquestrador): decompor fases, escrever briefings, arbitrar achados, verificação final.

## Como invocar sem os tipos registrados

Se a sessão não carregar os tipos de `.claude/agents/`, use o agente geral com `model` igual ao do arquivo e
comece o prompt com "Você é o agente `<nome>`; leia e siga `<caminho do arquivo>` e `GUARDRAILS.md`".
