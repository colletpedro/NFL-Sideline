# Contrato de pesquisa — produção em progressão e improvisação v1.0.0

Congelado em commit antes de calcular comparações por jogador. Pesquisa situacional descritiva; sem ajuste, regressão, ML, atribuição causal, seleção por nomes ou validação do vídeo. Integração visual posterior à revisão. Base: `01f23cfc64fee10f5b16dafae7eb4dabeff8579c`.

## Universo e identidade

Unidade: dropback PBP, chave única `(game_id, play_id)`; principal REG 2023–2025 e jogos atuais encerrados utilizáveis de 2026, sem exigir semana completa. 2022 somente auditoria separada. Selecionar `qb_dropback=1`, `play_deleted=0`, `qb_spike=0`, `qb_kneel=0`, `two_point_attempt=0`, `play_type in {pass,run}`. Flags de elegibilidade ausentes não passam. Corridas desenhadas, kneels, spikes, conversões, no_play, deletadas e POST ficam excluídos e auditados; overtime e penalidades com evento válido permanecem. `aborted_play=1` não será confundido com leitura: se o PBP ainda registra dropback elegível, conservar no universo como indeterminado. Sem excluir por EPA, nome ou posição.

Sacks: `play_type=pass,pass_attempt=1,sack=1,qb_scramble=0`. Scrambles: `play_type=run,pass_attempt=0,sack=0,qb_scramble=1,rush_attempt=1`. Lançamentos: `play_type=pass,pass_attempt=1,sack=0,qb_scramble=0`. Outros padrões/flags de evento inválidas → indeterminado/conflitante. PBP pass_attempt inclui sacks; não somar esse campo como número de lançamentos. Duplicatas ou chaves ausentes em cada fonte abortam; escolher exatamente uma revisão por temporada, nunca concatenar caches sobrepostos.

GSIS passer para lançamentos/sacks. Somente scramble estruturalmente válido pode usar rusher GSIS; conferir roster por temporada+semana+time (aliases LAR→LA,JAC→JAX,WSH→WAS), posição QB, identidade passer nula ou concordante, e evento run/scramble. Se falhar, identidade não resolvida e categoria indeterminada; não atribuir a outro jogador. Lançadores de outras posições permanecem separados. Identidades ausentes em lançamentos/sacks conservam jogada com status explícito; não somar como um jogador inventado. Troca de equipe conserva GSIS e conjunto de equipes.

EPA: campo `epa` original PBP, finito. Ausente/infinito → sem EPA válido, jamais zero; contagem da jogada conservada. FTN LEFT JOIN por chave, sem imputação de charting. Eventos sack/scramble podem ser conhecidos por PBP mesmo sem FTN; lançamentos sem flags/leitura necessárias permanecem indeterminados. Cobertura FTN sempre explícita.

## Definição congelada

Guardar leitura bruta e normalizada (`strip`, uppercase; nada de converter 2022 NA em primeira leitura). Auditoria cruzará ano × leitura × tipo de evento × throwaway × fora do pocket, incluindo nulos/códigos desconhecidos, flags desenhadas screen/RPO/trick/sneak e aborted.

Categorias exclusivas: `progression`, `scramble_drill`, `scramble`, `throwaway`, `sack`, `indeterminate`.

Antes da precedência, contradição estrutural dos eventos ou aborto → indeterminate. Depois sack → scramble validado → throwaway entre lançamentos → SD entre lançamentos → progressão (`0,1,2,CHK`, somente desde 2023) → indeterminate. Em 2022, `1,2,CHK` conhecidos ficam identificáveis na auditoria, sem comparação principal; `0` inesperado é indeterminado. `DES` designa lançamento desenhado **sem progressão**: conserva motivo `designed_no_progression` na categoria residual, sem alegar corrupção. Não chamar todo residual de dado ruim. Throwaway com código de leitura conserva ambos; precedência resolve sobreposição esperada. Throwaway junto de sack/scramble é contradição estrutural. SD sem lançamento conserva código como evidência secundária, nunca vira passe SD. Saída do pocket, segunda/terceira leitura, play action, screen e RPO isoladamente não definem improvisação. Contradição de charting binário, ou throwaway simultâneo a passe completo/interceptado, vai para residual.

Principal A=progression; B=scramble_drill+scramble. S1 B+=throwaway; S2 B+=throwaway+sack; S3 B=scramble_drill (somente lançamentos). A é idêntico em todas as versões. Categorias residuais e sacks/throwaways sempre visíveis. Não é uma divisão exaustiva de dropbacks dentro/fora da estrutura.

## Métricas e suporte

Por GSIS/temporada, todas as categorias e versões: n eventos, n EPA válido, soma, média EPA/jogada, jogos, frequência sobre **todos** os dropbacks do jogador e sobre classificáveis (todos menos residual), cobertura residual e de identidade. Soma sem EPA válido é indisponível. Média da liga ponderada por jogadas, QB auditados por roster, separada por temporada/condição. Todos os jogadores/posições permanecem nas tabelas completas; não calcular média simples de médias QB.

Diferença = média A − média B. Positivo significa maior produção observada em A; mostrar sempre A, B e volumes. Zero oportunidades → unavailable_no_opportunities; eventos sem EPA → unavailable_epa; suporte abaixo do corte → low_support, sem apagar valor descritivo.

Figuras principais: QB auditado, A com ≥100 EPA válidos, B com ≥25, ≥5 jogos com A ou B. S3 com <25 SD marcado com pouco suporte. Corte de legibilidade, sem garantia de robustez. Sem intervalos nesta primeira versão: heterogeneidade e definição ficam visíveis em temporadas/volumes/sensibilidades; não fabricar intervalo de habilidade. Sem ranking ou quadrantes valorativos.

História: cada temporada primeiro; sem agregado histórico principal. Pares adjacentes com o mesmo corte em ambas: Pearson/Spearman descritivos para níveis A/B, diferença, frequência B, taxa/soma sacks e composição; n pares explícito. Não prova habilidade persistente.

Diagnóstico de extremos: cinco maiores |EPA| por categoria/jogador, soma assinada/absoluta, contribuição para soma e mudança aritmética da média/diferença ao subtrair esses eventos **apenas como diagnóstico**; métrica principal não truncada. Contexto A/B: distribuição de descida, distância (≤3,4–7,8–10,11+), campo (red zone≤20,21–50,51+), quarto, segundos no quarto (≤120,121–600,601+), placar (≤−9,−8..−1,0,1..8,9+); ausências explícitas, médias/medianas e percentuais por grupo. Sem usar qb_hit/blitz/pocket como pressão completa.

## Exemplos e figuras

Critérios determinísticos em 2026, sem olhar nomes: (1) maior diferença entre legíveis com A acima da média da liga; (2) maior nível B entre legíveis; (3) menor |diferença|; (4) maior |diferença S2−principal|; (5) menor n B positivo entre QB com A≥100 e abaixo do corte B. Desempate GSIS. Duplicidade de exemplos permitida e reportada. Exportar todas as jogadas de cada exemplo e tabela das contribuições/extremos: chave, regra, flags, contexto, EPA, descrição literal da fonte. Não reconstruir culpa/intenção pelo texto.

Figuras PNG/SVG: distribuição categorias por ano; X=média B/Y=média A, referências de liga condicionais, nomes e suporte; frequência B/produção B; diferenças principal/S1/S2/S3; história por temporada com suporte. Diagonal de igualdade é diferença zero, não desempenho ideal.

## Reprodução e preservação

Fontes próprias copiadas após verificar manifest/hashes anteriores; atualizar somente em diretório novo, com classificação fixa, recebimento explícito, revisão por chave/campo, versões anteriores preservadas. Reproduzir offline em destino novo; verificar tanto bytes quanto equivalência numérica (tolerância explícita). Reconciliação independente SQL dos brutos, sem chamar classificador/agrupador principal. Testes offline nunca adquirem. Package index v1, métrica/classificação 1.0.0, evidências elementares e detalhes por jogador, fontes/hashes/status. Nada em ponteiros M3/B2, frontend, public/data, backend, DB ou ETL operacional. Sem merge/push/deploy, segredos ou serviços pagos.
