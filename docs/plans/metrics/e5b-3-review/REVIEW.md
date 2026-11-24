# Revisão do orquestrador — E5b-3, 09/10/2026

**Decisão: candidata com duas correções necessárias antes do aceite/E5b-4.**
Revisado o HEAD `767cf7f1d15f26022a7c4a982545a6c24c125134`, base
`8176e08668a6db4c837fb4de60f52d9b9011217e`. A implementação não foi incorporada
à branch de integração. Este registro fica na branch local de revisão;
main, candidato e escopos anteriormente aceitos permanecem preservados.

## Validação reproduzida

O verificador do candidato reproduziu 292 testes ETL, 26 exemplos/23 testes E5a,
12 hashes congelados, os seis arquivos da CLI E5b-1 byte a byte, dry-run E5b-2
sem banco/archive e os três exemplos temporais byte a byte. `git diff --check`
passou. A [verificação integral](verification.json) registra resultados/hashes.

A revisão leu contrato, desenho, matriz de razões, núcleo, validação, política de
evidência, conversão de instantes, CLI e testes pertinentes. A preservação de
precisão fracionária, distinção PIT/retrospectivo, fontes compostas inteiras,
agregação exata e premissas explícitas de confiança são compatíveis com a direção
do plano. Essas verificações não certificam dados históricos reais.

## 1. Temporada acumulada exige semanas fora do corte

Em `temporal_metrics/core.py:139`, SEASON_TO_CUTOFF usa todas as semanas do
calendário. A expectativa exige todas fechadas (`set(weeks) <= closed`), inclusive
a semana aberta do alvo e semanas futuras de um calendário completo da temporada.

Contraprova: na fixture existente, somente o jogo alvo passa da semana 1 para a
semana 4 já declarada no pedido. Os três eventos elegíveis, suas fontes, somas e
provas das semanas anteriores não mudam. O alvo continua excluído por ID.
Mesmo assim, expectedGames passa de 3 para null, exclusivamente por
PERIOD_NOT_CLOSED da semana 4. Um calendário completo real tende a manter esse
bloqueio enquanto existir uma semana futura aberta.

Correção requerida: definir e implementar a expectativa da temporada **até o
corte**, separando eventos fora do período, alvo excluído e eventos cuja posição
temporal é realmente incerta. Não basta remover PERIOD_NOT_CLOSED, usar apenas
jogos com métricas ou deduzir encerramento pelo número da semana. Provas ausentes
de eventos potencialmente pertencentes ao recorte precisam continuar UNKNOWN;
jogos encerrados elegíveis sem PBP precisam continuar no denominador.

Adicionar propriedades com calendário completo da temporada, alvo em semana
aberta, jogo comprovadamente futuro, jogo iniciado/encerramento incerto,
reagendamento e jogo elegível sem fonte. A mesma distinção deve ser explícita na
referência histórica quando aplicável, sem alargar a janela de últimas semanas.

## 2. Comparação ignora os parâmetros do recorte

Em `temporal_metrics/core.py:408`, comparison confere o nome da janela, temporada,
fase, origem, modo e corte, mas ignora requestedWeeks/semana solicitada.

Duas contraprovas, com agregados individualmente elegíveis:

- LAST_3_CALENDAR_WEEKS com semanas [1] versus [1, 2] retorna elegível sem falhas.
  Usa a fixture original; a segunda semana é bye, mantendo os valores numéricos.
- WEEK_OBSERVATION da semana 1 versus 3 também retorna elegível sem falhas,
  mesmo com EPA de passe 1/2 versus -1/3. Esse segundo cenário é uma variação
  materializada sintética: remove gap e EPA ausente, conservando as invariantes
  dos 12 grupos. Não constitui recálculo autenticado de PBP real.

Correção requerida: uma assinatura explícita e normalizada do período solicitado,
com rejeição tipada de recortes incompatíveis e preservação dos valores originais.
Não exigir igualdade de gameIds, time ou identidade do resultado: adversários
têm eventos diferentes. Não usar actualWeeks como substituto de requestedWeeks:
byes e fontes ausentes não mudam a definição da janela.

Testar semana diferente, janelas recentes diferentes, mesmos recortes com eventos
distintos, bye/lacuna e representação equivalente da assinatura.

## Reproduzir as contraprovas

No checkout desta revisão, com Python/dependências já instalados, apontar para
um checkout do HEAD candidato acima e usar um arquivo de saída novo:

```bash
PYTHONDONTWRITEBYTECODE=1 etl-pipeline/.venv/bin/python -B \
  docs/plans/metrics/e5b-3-review/reproduce.py \
  --candidate '/Users/pedrocollet/.codex/worktrees/metrics-temporal-e5b3/NFL Sideline' \
  --output /tmp/nfl-e5b3-counterexamples-novo.json
```

As três contraprovas foram executadas; [resultados](counterexamples.json).
O script exige o HEAD exato, não altera o candidato e não usa banco/rede.

## Próxima entrega

Corrigir na frente E5b-3 antes de criar o materializador E5b-4. Atualizar
contrato/matriz de razões e versionar a mudança de comportamento do algoritmo;
preservar os exemplos 1.0.0 como evidência histórica, sem substituição silenciosa.
Reexecutar o gate offline e acrescentar as propriedades acima. Não é necessário
repetir PostgreSQL, Java ou frontend nesta correção de núcleo Python.

Após o aceite, E5b-4 continuará exigindo materializador explícito das relações
E5b-2 e contrato Java separado. Não há prova automática de disponibilidade,
ingestão, encerramento, completude ou modelo EPA históricos. A verificação de
Supabase completo/advisors permanece pendência independente antes de aplicar
migrations fora do PostgreSQL descartável.

Nenhum banco, Docker, .env, aquisição, geração externa, snapshot público,
aprovação, push, deploy ou merge foi executado nesta revisão.
