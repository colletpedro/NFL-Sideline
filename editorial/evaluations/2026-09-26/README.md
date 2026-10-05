# Avaliação editorial interna — 26/09/2026

Este diretório não participa do build estático e não constitui aprovação editorial.

**Resultado em 27/09:** 6/10 tentativas autorizadas, nenhuma resposta de análise; última falha HTTP 402. Os reservados não foram enviados. Consulte [REVIEW.md](REVIEW.md) e [attempt-ledger.json](attempt-ledger.json).

## Desenho congelado antes da geração

`cases.json` fixa quatro casos de desenvolvimento e dois reservados. A seleção usou apenas as entradas, antes de observar qualquer resposta nova. O prompt pode ser ajustado a partir dos quatro casos de desenvolvimento; depois de congelar prompt e renderer, os dois reservados são gerados uma vez. Falhas e rejeições contam no resultado, sem regeneração seletiva para escondê-las. Replay de uma resposta antiga não conta como nova geração real.

| Papel | Jogo | Motivo |
|---|---|---|
| Desenvolvimento | ARI–SF, 2026 W3 | Extremo semanal no passe de SF; mudança de sinal em ARI |
| Desenvolvimento | BAL–DAL, 2026 W3 | Oportunidade ataque–defesa; contraponto à tese |
| Desenvolvimento | NE–JAX, 2026 W3 | Sinais conflitantes entre semanas |
| Desenvolvimento | CHI–BAL, 2025 W8 | Semanas desencontradas: CHI 4/6/7, BAL 4/5/6 |
| Reservado | SEA–WAS, 2026 W3 | Transferência para outra oportunidade ataque–defesa |
| Reservado | MIN–TB, 2026 W3 | Transferência para sinais divergentes |

CHI–BAL é uma avaliação retrospectiva com as métricas hoje armazenadas. Não sabemos se essas mesmas versões estavam disponíveis em 23/10/2025; essa data é apenas o corte de semanas do cenário. O caso nunca é candidato a publicação atual. Nos casos de 2026, preservamos o contexto efetivamente guardado em 22/09/2026, sem completar com a base atual.

## Origens e integridade

- `regression/originals.json`: leitura de `analysis_cache` IDs 56–71, conforme identificação explícita do usuário; contém o texto serializado original e o contexto armazenado.
- `regression/published-originals.json`: cópia dos 16 textos públicos, para comparação futura sem depender de um snapshot mutável.
- `regression/integrity.json`: 16/16 hashes de resposta e prompt conferem com as seleções FULL de 22/09; 16/16 textos conferem com o snapshot.
- `regression/uneven-source.json`: seis linhas reais de `team_week_metrics`, temporada 2025, CHI/BAL, semanas 4–7. Nenhuma semana foi suprimida artificialmente.
- `contexts/` e `uneven-context/`: adaptação para evidências e janelas v3 exclusivamente a partir dessas entradas; mercado não é enviado à geração tática.
- `provenance/`: prompt e renderer anteriores a ajustes.

As críticas anteriores por jogo não estão disponíveis nesta tarefa. Os critérios abaixo são uma nova formalização verificável, não uma transcrição dessas críticas.

## Rubrica fixada

Pontuar cada item de 0 a 2: 0 = problema material, 1 = parcialmente satisfatório, 2 = satisfatório. Uma validação de claims bem-sucedida não substitui a leitura editorial.

1. **Tese relevante:** identifica um encontro ataque–defesa que organiza o confronto; não transforma um extremo semanal em identidade permanente nem apenas compara dois ataques sem explicar o adversário.
2. **Contraponto útil:** qualifica a tese com evidência contrária pertinente ou limitação específica; não reforça o favorito sob o rótulo de alerta. Não exigir evidência que a entrada não contém.
3. **Explicação:** liga os recortes ao confronto sem inventar lesões, play-action, causalidade, força relativa à liga ou garantia de resultado.
4. **Fluidez:** cada seção acrescenta informação; não repete integralmente evidências, números e ressalvas. Mantém unidades, recortes e natureza da média legíveis.

Rejeição técnica impede avaliação do texto, não recebe uma nota editorial inventada. Para recomendar ampliação do lote: nenhuma rejeição pendente, nenhum item 0 e nenhum problema material novo nos reservados. Esta recomendação ainda não autoriza publicação.

## Regressão dos 16 originais

O teste `EvaluationApplicationTest` verifica as 16 entradas congeladas: data de referência, apenas semanas 1/2 de 2026, conservação de cada métrica e volume presentes, e ausência de mercado no contexto tático. Não exige claims v3 dos textos legados, nem lhes atribui conhecimentos posteriores. A regressão mecânica não comprova melhora editorial nos dez jogos fora do lote real.

Critérios comuns: nunca acrescentar semanas; não preencher `earlyDownEpa`/`explosivePlayRate` nulos; não confundir sucesso permitido pela defesa com sucesso defensivo; não usar dropback como eficiência; manter contrapontos ao concluir; não inferir força permanente com duas observações. As expectativas específicas constam em `regression/criteria.json`.

## Reprodução

Construir com Java 21: `mvn -o -f core-api/pom.xml clean verify`.

O comando `editorial-evaluate` não inicia Spring, não conecta ao banco e não grava `analysis_cache`. Os diretórios de saída precisam ser novos; o pai já deve existir.

```sh
java -jar core-api/target/core-api-0.1.0.jar editorial-evaluate prepare \
  editorial/evaluations/2026-09-26/regression/originals.json /tmp/contextos-novos

# Requer GEMINI_API_KEY no ambiente e autorização para envio ao provedor.
java -jar core-api/target/core-api-0.1.0.jar editorial-evaluate generate \
  editorial/evaluations/2026-09-26/cases.json development /tmp/avaliacao-dev-nova

# Após congelar os ajustes, sem adaptar o prompt às respostas reservadas:
java -jar core-api/target/core-api-0.1.0.jar editorial-evaluate generate \
  editorial/evaluations/2026-09-26/cases.json holdout /tmp/avaliacao-reservada-nova
```

Cada execução preserva manifesto, hash do manifesto, prompt, configuração de geração, modelo e horário. Cada caso guarda contexto, user prompt, resposta original exata, claims quando o JSON é legível, rejeição categorizada ou quatro textos renderizados. Erros de transporte são registrados sem corpo remoto nem credenciais. Uma execução offline `replay <manifesto> <split> <nova-saída> <execução-anterior>` revalida as mesmas respostas e não chama Gemini.

## Publicação

Nenhum artefato daqui é uma seleção aprovada. Para publicar: gerar para o contexto elegível → revisar → obter aprovação → registrar seleção e hashes da linha de cache correspondente → exportar snapshot → revisar/versionar → publicar. Reavaliar elegibilidade e profundidade no dia da geração/publicação; contextos congelados de regressão não tornam jogos passados elegíveis. O frontend pode ser publicado separadamente após revisão e versionamento do seu diff; esse deploy não atualiza análises.

## Execução autorizada e falhas

`run_authorized.py` verifica hashes do manifesto e dos seis contextos antes de invocar o Java. Reservas e tentativas são registradas separadamente; falha também consome orçamento. `resume` no avaliador só visita casos cujo diretório ainda não existe e nunca repete uma tentativa. O comando para ao primeiro erro de geração, preservando status HTTP e classes de exceção sem corpo remoto ou segredos. O histórico desta execução inclui um ajuste experimental de transporte posteriormente retirado; as versões utilizadas estão em `provenance/`. Não executar nova rodada sem antes revisar o relatório e resolver o impedimento externo.
