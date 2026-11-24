# Classificação exclusiva e auditável · 1.0.0

A unidade é `(game_id, play_id)` do PBP, com exatamente uma revisão de PBP e FTN por temporada. [Contrato congelado](RESEARCH-CONTRACT.md) e [implementação](../../../research/qb_structure_production/classify.py). Esta classificação separa eventos e evidência de progressão; não identifica causalmente toda quebra da estrutura ofensiva.

## Elegibilidade

REG, `qb_dropback=1`, `play_deleted=0`, `qb_spike=0`, `qb_kneel=0`, `two_point_attempt=0` e `play_type=pass/run`. Todas as flags devem ser explícitas. Inclui overtime e penalidade quando o evento válido continua registrado como pass/run. Exclui POST, corridas desenhadas (mesmo de QB), kneels, spikes, conversões, no_play e deleted. Falhas dos critérios ficam em `audit/excluded_YYYY.parquet`, com motivos cumulativos. Nenhum filtro de EPA ou posição elimina uma elegível.

`aborted_play=1` dentro desse universo permanece com categoria indeterminada; não se reconstrói uma leitura a partir da descrição. Flag de aborto ausente/inválida também impede classificação conhecida. EPA ausente conserva o evento, sem preencher zero.

## Tipos de evento e precedência

| Tipo estrutural | play_type | sack | qb_scramble | pass_attempt | rush_attempt |
| --- | --- | --- | --- | --- | --- |
| Sack | pass | 1 | 0 | 1 | 0 |
| Scramble candidato | run | 0 | 1 | 0 | 1 |
| Lançamento | pass | 0 | 0 | 1 | 0 |

Outro padrão ou flag ausente/inválida é conflito. A checagem vem **antes** da precedência: sack+scramble não é simplesmente sack. Throwaway junto de sack/scramble, ou throwaway junto de passe completo/interceptado, também fica no residual. Não se consulta sinal de EPA, texto ou nome para resolver conflito. Flags binárias FTN fora do domínio são conflitos; ausência não vira false.

| Ordem após checagem | Categoria | Regra/evidência |
| --- | --- | --- |
| 1 | `sack` | padrão PBP sack válido, não abortado |
| 2 | `scramble` | padrão run/scramble + rusher GSIS verificado por roster, posição QB, passer ausente ou concordante |
| 3 | `throwaway` | lançamento + FTN presente + is_throw_away=true; código de leitura original conservado |
| 4 | `scramble_drill` | lançamento + FTN + throwaway=false + read normalizada SD |
| 5 | `progression` | lançamento + FTN + throwaway=false + 0/1/2/CHK |
| 6 | `indeterminate` | DES sem progressão, aborto, ausência, corrupção ou tipo de scramble não-QB |

As regras conservam o tipo de evento separado da categoria. Um sack com SD continua sack. Um scramble com SD continua scramble, se verificado; nunca vira passe SD. PBP identifica sack/scramble mesmo sem charting; esse caso preservaria cobertura FTN ausente. Lançamentos sem charting ou sem flag de descarte permanecem indeterminados. Campo fora do pocket não é requisito de A/B, nem prova de improvisação. Códigos de segunda/terceira leitura tampouco provam quebra da jogada.

## Leitura, desenho e histórico

`read_thrown` é preservado bruto. `read_normalized` usa apenas strip e uppercase; `0` continua string, e NA continua ausência. `0,1,2,CHK` são agrupados como progressão registrada conforme dicionário; `DES` é lançamento desenhado **sem progressão** e não entra em A. O residual distingue explicitamente `designed_no_progression` de corrupção/ausência. Screen/RPO/play action/trick/sneak ficam como flags secundárias; não há nesta base uma flag geral que identifique todo rollout ou toda corrida desenhada. Não inferir desenho só por QB estar fora do pocket.

Em 2022, `0` não é documentado e seria conflito; NA nunca é imputado como primeira leitura. Os demais códigos conhecidos ficam rastreáveis, mas **nenhum agregado principal, figura comparativa ou correlação usa 2022**. Os cruzamentos por evento/ano estão em [auditoria](DATA-AUDIT.md).

## Identidade

Passer GSIS para lançamento/sack. Rusher GSIS somente em evento estrutural run+scramble, com roster REG de mesma temporada/semana/time. Aliases: LAR→LA, JAC→JAX, WSH→WAS. Não preencher um passer ausente com rusher em qualquer outro evento. Identidade é GSIS, não nome nem equipe. Troca de equipe conserva um jogador e lista suas equipes.

Um WR auditado em scramble conserva seu GSIS, nome e `position_class=other`, mas fica no residual `scramble_non_qb_position`; não é uma identidade desconhecida nem um scramble de QB. Se faltarem roster/GSIS ou houver contradição passer/rusher, manter status `unknown_or_conflicting`, com motivo. Nenhum jogador é escolhido por aproximação textual. Nesta aquisição todas as identidades são resolvidas.

## Evidência por linha e reconstrução

`plays.parquet` guarda categoria, `rule`, `reason`, `event_type`, `evidence_used`, flags PBP/FTN originais, leitura bruta/normalizada, cobertura, fonte de identidade, contexto, EPA válido e descrição PBP. `players/{gsis}.json` inclui todas as linhas e comparações. Motivo nulo é esperado apenas para categorias conhecidas; residual sempre tem motivo.

A=`progression`. Principal B=`scramble_drill+scramble`; S1 soma `throwaway`; S2 soma também `sack`; S3 usa só `scramble_drill`. Nada precisa ser reclassificado para alternar definições. As somas/contagens elementares são suficientes para reconstruí-las. Throwaways e sacks não são apagados nem presumidos como quebra da estrutura na definição principal.
