# Protocolo E4 congelado antes dos ajustes

Base exata `793ac7b`; método: inspeção interna pelo agente, sem participantes ou tempos humanos. Matriz e critérios em [protocol.json](protocol.json). Todos os 20 estados E1 serão inspecionados no navegador; BAL–DAL, CHI–BAL e NE–JAX serão comparados com seus textos completos. Os 17 documentos E2 continuam regressões automatizadas.

Tarefas equivalentes para texto e visual: identificar ataque/defesa e fundamento; informar temporada/semanas; apontar achado e restrição principal; reconhecer ausência ou semanas diferentes; explicar por que o achado não escolhe vencedor. Registrar disponibilidade/localização das respostas, densidade, repetição e ambiguidades antes/depois, sem transformar isso em acerto humano. A hipótese 10–15 s permanece sem validação.

Estados: oportunidade, oposição, ataque não demonstrado, ambos negativos, variação, zero, sinais pequenos positivos/negativos, empates, oportunidades dos dois lados, unilateral, ausência, histórico, lacunas, duas semanas, geral agrupado, semanas diferentes, outlier e relação independente. Tipo/proveniência por caso no JSON; nenhum é holdout.

O inventário adicional procurou contextos v3 em editorial e testes. O censo histórico já incluiu as fontes locais; cópias e fixtures não demonstram independência. Não há amostra comprovadamente não utilizada no ajuste.

Operação usa somente esta worktree e `/tmp/nfl-e4-20261007`, com processos próprios nas portas 18081/18083 se livres. Sem .env, banco, ETL ou modelos. Ampliar texto para 200% mantendo viewport, com CSS temporário servido apenas para a avaliação, e registrar tamanhos computados. Não chamar redução de viewport de zoom.

Critério de saída mecânico: contrato e números preservados, propriedades significativas, desktop/mobile, teclado/tabelas/foco, ampliação, recuperação, frontend/lint/build/Python/diff e isolamento público. Critério de compreensão humana permanece pendente sem respostas reais.
