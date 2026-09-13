# Contrato público de snapshots

O frontend de Production lê somente arquivos versionados em `web-ui/public/data`. O contrato atual é `schemaVersion: 1`; mudanças incompatíveis exigem nova versão e suporte explícito no cliente.

## Manifesto

`/data/manifest.json` contém:

- `schemaVersion`: inteiro `1`;
- `generatedAt`: timestamp ISO-8601 em UTC;
- `defaultSeason`: temporada aberta por default;
- `seasons`: temporadas disponíveis, únicas e em ordem crescente.

## Temporada

`/data/seasons/{season}.json` contém:

- `schemaVersion`, `season` e `generatedAt`;
- `teams`: times públicos em ordem de `teamAbbr`;
- `games`: jogos em ordem de semana, data e `gameId`;
- `metricsByTeam`: mapa ordenado por abreviação; cada série é ordenada por semana;
- `analysesByGame`: mapa ordenado por `gameId` com, no máximo, a análise `matchup` válida mais recente.

Cada jogo referencia `homeTeamAbbr` e `awayTeamAbbr`, evitando repetir o cadastro completo dos times. Ele preserva calendário, scores, `result`, linhas, moneylines, odds, informações públicas do estádio e o snapshot de mercado. Métricas aparecem uma única vez por time/semana, e o frontend monta `GameDetail` em memória.

Calendário independe de mercado: `market: null` e odds nulas são publicáveis. Um par de moneylines completo e válido atualiza atomicamente o par e o mercado; ausência/parcialidade posterior preserva a última cotação completa, sem combinar observações diferentes. Spread/total ausentes também preservam linhas conhecidas. `rows_games` do ETL conta todo o calendário preparado; `rows_market` conta apenas os mercados calculados/upsertados na execução. A UI não fabrica probabilidade, favorito, confiança ou edge na ausência de sinal válido. Análise disponível continua acessível. PBP ausente produz ausência honesta de métricas da temporada.

`defaultSeason` é a fonte da temporada da Home/header/footer em Production, e `generatedAt` é a data de publicação exibida. A API local oferece contexto equivalente. A semana inicial depende apenas do calendário: intervalo inclusivo contendo a data UTC atual; entre semanas, próxima semana com jogo; antes da temporada, primeira; após a temporada, última. A função aceita data injetada em testes. Seleção manual continua disponível.

A análise pública expõe somente `gameId`, `analysisType`, `createdAt`, `fatorChave`, `vantagemTatica`, `alertaVermelho` e `veredito`. `context_json`, `prompt_hash`, nome do modelo, prompts, credenciais e configurações internas são proibidos.

### Tipos e campos da versão 1

Tipos marcados com `?` aceitam `null`. Valores decimais são números JSON e timestamps são strings ISO-8601 UTC.

| DTO | Campos |
|---|---|
| `Manifest` | `schemaVersion: integer`, `generatedAt: timestamp`, `defaultSeason: integer`, `seasons: integer[]` |
| `SeasonSnapshot` | `schemaVersion: integer`, `season: integer`, `generatedAt: timestamp`, `teams: Team[]`, `games: Game[]`, `metricsByTeam: Record<string, Metric[]>`, `analysesByGame: Record<string, Analysis>` |
| `Team` | `teamAbbr: string`, `teamName: string`, `conference: string?`, `division: string?`, `logoUrl: string?` |
| `Game` | `gameId: string`, `season: integer`, `week: integer`, `gameType: string`, `gameday: date?`, `homeTeamAbbr: string`, `awayTeamAbbr: string`, `homeScore: integer?`, `awayScore: integer?`, `result: integer?`, `spreadLine: decimal?`, `totalLine: decimal?`, `homeMoneyline: integer?`, `awayMoneyline: integer?`, `homeSpreadOdds: integer?`, `awaySpreadOdds: integer?`, `overOdds: integer?`, `underOdds: integer?`, `roof: string?`, `surface: string?`, `divisionGame: boolean?`, `updatedAt: timestamp?`, `market: Market?` |
| `Market` | `homeImpliedRaw: decimal?`, `awayImpliedRaw: decimal?`, `homeImpliedFair: decimal?`, `awayImpliedFair: decimal?`, `vigPct: decimal?`, `computedAt: timestamp?` |
| `Metric` | `season: integer`, `week: integer`, `teamAbbr: string`, `offEpaPlay: decimal?`, `offEpaPass: decimal?`, `offEpaRush: decimal?`, `defEpaPass: decimal?`, `defEpaRush: decimal?`, `dropbackRate: decimal?`, `playsOffense: integer?` |
| `Analysis` | `gameId: string`, `analysisType: "matchup"`, `createdAt: timestamp`, `fatorChave: non-empty string`, `vantagemTatica: non-empty string`, `alertaVermelho: non-empty string`, `veredito: non-empty string` |

O valor de `result` conserva o contrato atual do banco (`homeScore - awayScore`). Campos opcionais permanecem presentes no JSON como `null`, mantendo o shape estável.

## Garantias do exportador

A temporada usa três consultas de domínio, independentemente da quantidade de jogos: jogos com times e mercado; métricas; caches `matchup` dos IDs da temporada. Não há lazy loading durante a serialização porque entidades JPA nunca são serializadas.

O conteúdo é gravado em um diretório temporário irmão e só então trocado. Se a troca falhar, a saída completa anterior é restaurada. Quando apenas `generatedAt` mudaria, os arquivos existentes são preservados; assim, o timestamp continua representando a geração do conteúdo material publicado e diffs semânticos permanecem pequenos.

## Comando

Após empacotar o Java 21:

```bash
java -jar core-api/target/core-api-0.1.0.jar snapshot-export \
  --season 2026 \
  --output web-ui/public/data
```

`--season` pode ser repetido e aceita também `--season=2026`. Sem ele, o exportador usa a temporada NFL corrente. Uma temporada sem jogos falha, salvo quando `--allow-empty` é informado explicitamente.

Falhas batch emitem códigos fixos úteis para CI (`INVALID_OPTIONS`, `STARTUP_FAILED`, `DATABASE_READ_FAILED`, `OUTPUT_WRITE_FAILED`, `EMPTY_SEASON` ou `EXPORT_FAILED`) com orientações sanitizadas; mensagens de exceção, URLs de banco e payloads não são impressos.

O snapshot público atual não deve ser substituído por resultados de validação local. O rollout posterior exige autorização para atualizar o remoto, exportar read-only preservando caches e só então versionar/publicar o artefato definitivo.
