# Documento visual interno v1

Status: contrato de implementação fechado na preparação E1. **O projetor Java e o cliente visual integrado ainda não existem.** Este contrato não altera claims v5, HTTP 1.1.0 nem snapshot público v1. A Spec continua normativa para o produto existente.

Fontes normativas desta entrega: [schema JSON](schema.json), [vocabulário](copy-catalog.json), regras abaixo e [matriz de estados](../../../docs/plans/visual-v1/states.md). Conflitos exigem ajuste versionado coordenado pela integração, antes de backend/frontend divergirem.

## Objetivo e limites

Transformar um resultado validado do seletor local 2.0.0 em uma apresentação factual. Quatro encontros de passe/corrida são visíveis; os dois panoramas gerais permanecem acessíveis quando acrescentam informação ou foram agrupados. Não introduzir probabilidades próprias, confiança, score, limiar de relevância, inferência causal ou cálculo de winner/edge.

O primeiro documento contém **pontos semanais**, não médias novas de período. Cada ponto já é uma média semanal do contexto original. Adiar médias de temporada, percentis, métricas situacionais e comparação automática entre versões à entrega correspondente. Os quatro textos antigos continuam na consulta legada.

## Shape e origem

| Campo | Semântica |
| --- | --- |
| `schemaVersion` | `visual-analysis-1.0.0`; independente de claims/artifact/snapshot |
| `projectorVersion` | `visual-projector-1.0.0`; reserva para a implementação E2 |
| `mode`, `publicationApproved` | Somente local e `false` nesta versão |
| `source` | `CONTRACT_FIXTURE` com ID sintético **ou** `VALIDATED_LOCAL_RESULT` com identidade real, hash canônico do contexto, claims 5 e seletor 2.0.0 |
| `game` | ID opaco, times distintos, temporada, semana e fase do contexto congelado |
| `scope` | Pregame; data declarada opcional; garantia limitada à ordem das semanas; semanas esperadas e ausência de ajuste por adversário |
| `evidence` | Observações semanais de seis métricas EPA; valor decimal exato, texto formatado, time/período/origem e denominador realmente conhecido |
| `series` | IDs e referências ordenadas às observações; nenhum número duplicado |
| `encounters` | Exatamente seis posições: cada ataque × defesa adversária em PASS, RUSH, GENERAL |
| `findings` | Claims MATCHUP v5 resolvidas, com referência ao encontro, relação, padrões observados e uma restrição principal |
| `restrictions` | Limitações tipadas, referências e texto controlado; origem em claim ou fato verificável do contexto |
| `links` | Relações adicionais já validadas entre achados; não incluem auto-referência |
| `presentation` | Destaques, equivalência, avisos globais e política única de escala |

IDs são opacos. Consumidores não extraem time, métrica ou semana de `tw:...`, de `gameId`, de `claimId` ou da grafia de outro ID. A correspondência com a origem é responsabilidade do projetor e seus testes de reconciliação.

`CONTRACT_FIXTURE` serve exclusivamente a testes e ao estudo visual, sempre rotulado como sintético. A API real recusa esse modo como saída de geração. Os hashes reais não são simulados nos exemplos. Nenhum exemplo desta pasta é resultado real do motor ou evidência de qualidade editorial.

## Semântica e validação obrigatória no Java

1. Executar a seleção/validação v5 existente antes da projeção. Partir de claims e candidatos **resolvidos pelo validador**, não confiar na cópia de `selection.candidates` da auditoria.
2. Reconciliar cada evidência com contexto canônico: identidade, valor exato, métrica, time, temporada, semana, origem e volume. Reconciliar séries com `EvidenceWindow` validada. Não usar séries atuais do banco para explicar um resultado antigo.
3. `claimId` de finding corresponde a MATCHUP/SIGNAL_PROFILE. Seu encontro, relação e padrões devem ser os mesmos da claim resolvida. Todos os encontros pairable entram uma única vez como finding ou agrupamento v5 validado. Nenhuma claim adicional é inventada para completar uma grade.
4. `COMPARABLE` significa pairable na regra v5: ambas as janelas têm a mesma temporada/origem. **Não significa mesmas semanas, cobertura adequada ou significância estatística.** Semanas diferentes podem ser comparáveis, com restrição de cobertura. `UNAVAILABLE` preserva a série unilateral e informa MISSING_ATTACK, MISSING_DEFENSE, MISSING_BOTH ou INCOMPATIBLE_ORIGIN.
5. `REPRESENTED_BY` é exclusivo de GENERAL omitido por `GENERAL_SAME_SIGNAL_AND_COVERAGE`. Preservar séries e referências, sem afirmar igualdade numérica. O backend prova `SignalEditorialPolicy.redundantGeneral`; o browser não agrupa por conta própria.
6. Relações e padrões são os enums de `SignalDimensions`. Não reclassificar com números arredondados. POSITIVE_CONVERGENCE exige exatamente a cobertura v5; POSITIVE_COMPATIBILITY_ONLY não vira oportunidade por aparência do gráfico.
7. Destaques são as claims MATCHUP de `fator_chave`. Caso essa seção contenha somente limitação global, `highlightFindingIds` fica vazio. Havendo múltiplos destaques, um grupo contém exatamente todos eles; nenhum desempate por nome, valor ou posição. A ordem dentro do grupo é somente apresentação.
8. `links` projeta apenas ADDITIONAL_RESTRICTION e INDEPENDENT_OPPORTUNITY já validadas. INTERNAL_LIMITATION vira restrição vinculada; DIRECT_CONFLICT não pertence a v5. Oportunidade independente não é refutação. Origem dos links é um finding fora dos destaques e destino é um destaque, conforme v5.
9. `primaryRestrictionId` é obrigatório em cada finding. Preferir sua WINDOW_LIMITATION vinculada, quando existir. Para achados secundários sem essa claim, usar um fato de cobertura/recorte derivado e verificado, com `claimId: null`. Isso não cria uma claim v5 nova. Escolha determinística: referência histórica → cobertura insuficiente → variação de sinal → até duas observações → limite do recorte.
10. Toda restrição tem condição comprovável: SAMPLE_LIMIT exige no máximo duas observações em uma das séries; SIGN_VARIATION_LIMIT exige sinal misto; COVERAGE_LIMIT exige inadequação na regra v5; HISTORICAL_ONLY exige referência histórica; UNEVEN_WINDOWS exige semanas distintas; NO_DATA/PARTIAL_DATA exigem a ausência correspondente. UNAVAILABLE_DENOMINATORS exige volume desconhecido para o fundamento. LIMITED_SCOPE descreve somente o recorte disponível. Claims globais SMALL_SAMPLE/LIMITED_WINDOW mapeiam para SAMPLE_LIMIT/LIMITED_SCOPE sem alterar os documentos antigos.
11. `claimId` não nulo de restriction deve existir na validação v5 e sustentar o código. Sem claim, preservar `encounterIds`/`evidenceIds` necessários à verificação do fato. Avisos de metodologia globais têm arrays vazios e condição no scope. O catálogo controla textos, não autoriza afirmar uma restrição falsa.
12. O vocabulário em `copy-catalog.json` é finito e faz parte da versão da projeção. Sem texto livre do seletor. Datas e nomes de times entram em rótulos estruturados escapados, não em HTML.

O script Python de fixtures verifica estrutura e condições observáveis. **Não substitui esses doze requisitos**: não tem o contexto/claims original, não prova cobertura v5 completa, não valida a pertinência de todos os contrapontos e não pode certificar origem apenas porque recebeu um hash.

## Números, amostra e período

- `value` é string decimal sem exponencial; `displayValue` é produzido pelo Java com HALF_UP, sinal e três casas. Zero exato aparece `0,000`; módulo não zero menor que 0,0005 usa as desigualdades do renderer atual. A UI não converte valor arredondado em classificação.
- `unit` é EPA_PER_PLAY; o fundamento determina “por jogada classificada como passe/corrida”. As definições atuais da fonte, incluindo sacks/scrambles, permanecem até E5. Não chamar EPA/pass de dropback ajustado.
- `plays: null` significa desconhecido. Passe/corrida têm volume desconhecido no contexto atual: não usar playsOffense/Defense total. Para GENERAL, copiar o volume elegível disponível. Número de semanas é mostrado separadamente.
- `series.evidenceIds` ordena por semana crescente; sem interpolação, médias novas, preenchimento com zero ou cópia da outra temporada.
- Origens atuais exigem temporada do jogo e semana estritamente anterior. Históricas exigem temporada anterior e rótulo visível. O recorte atual não oferece garantia por instante de disponibilidade, nem por jogo individual.
- `expectedCurrentWeeks` espelha `EditorialParameters.expectedRecentWeeks`; é uma política mecânica, não prova que o time jogou nessas semanas. Ausência não distingue bye de falha de ingestão.
- `declaredAsOfDate` vem de metadado permitido da origem ou null, sem alterar a seleção ou aumentar a garantia temporal. Não fabricar gameday/adversário de cada observação.
- Gráficos podem converter o decimal para coordenada finita, sem reclassificar a análise. Overflow/underflow para zero exige fallback acessível para a tabela exata, sem plotar um ponto falso. Colisão subpixel normal é permitida; os números continuam legíveis.

## Política visual fechada para o experimento

`SHARED_SYMMETRIC_ZERO_V1`: eixo horizontal assinado, simétrico em torno de zero. Extensão M = maior módulo de **todas** as observações do documento, incluindo panoramas recolhidos; domínio [-M,+M]. Para todas as observações zero, usar [-0,1,+0,1] apenas como escala de desenho, sem limiar analítico. Sem dados: não desenhar gráfico. Na comparação futura de versões, usar a união de ambos os documentos.

Todos os pontos/extremos ficam dentro da área; zero é rotulado. Ataque usa círculo e defesa usa losango, com rótulos textuais. EPA permitido menor é melhor para defesa; o eixo mantém o sinal original. Não somar/subtrair séries. A dimensão de um gráfico isolado não é comparável à de outro contexto que tenha escala diferente.

Ordem de navegação: visitante passe, visitante corrida, mandante passe, mandante corrida; geral em detalhe. Destaques ficam na leitura rápida com igualdade visual para empatados. Não esconder o segundo time. Restrição principal, período e volume desconhecido ficam visíveis; definição, tabela e texto adicional expandem. Mercado separado e ausente nestas fixtures.

A cor lima marca interação/destaque editorial, não probabilidade de vitória. Cor não é o único canal. Alvos de interação de 44 px, foco visível, contraste de texto ≥4,5:1 e elementos gráficos essenciais ≥3:1, tabela acessível e ausência de conteúdo necessário apenas em hover. Wireframe não equivale a auditoria formal WCAG ou avaliação de compreensão.

## API e persistência a implementar em E2

Rota aditiva proposta e fechada para coordenação: `GET /api/v1/local-analysis/{gameId}/{attemptId}/insights`.

Resposta 200:

```json
{
  "mode": "LOCAL_RULES_DEVELOPMENT",
  "publicationApproved": false,
  "gameId": "ID_DO_CONTEXTO",
  "attemptId": "UUID_DA_TENTATIVA",
  "resultIdentity": "SHA256_REAL_DO_RESULTADO",
  "visualIdentity": "SHA256_DOS_BYTES_PERSISTIDOS_DE_INSIGHTS_JSON",
  "document": "VisualAnalysisDocument: objeto conforme schema, não string"
}
```

O exemplo acima explica o envelope; placeholders não são uma fixture válida. O backend testa igualdade entre envelope, documento e tentativa consultada.

- Resultado legado sem visual: 409 com `error: VISUAL_DOCUMENT_NOT_AVAILABLE`. A UI conserva a leitura textual e informa compatibilidade; não regenera ao fazer GET.
- Tentativa inexistente: 404; corrupção/incompletude: 409 `LOCAL_RESULT_UNAVAILABLE`. Erros já existentes de rota/request preservados.
- Novo artefato interno v4 inclui `insights.json` e seu hash, com leitura explícita v3/v4. Não alterar resultados v3. Identidade semântica existente continua; identidade visual é o SHA-256 dos bytes UTF-8 persistidos do documento. Ordenação determinística e ausência de timestamp de tentativa no documento tornam a projeção reproduzível; arquivos CSS não participam do hash.
- POST e GET textual mantêm envelopes anteriores. Novo endpoint não publica contexto, prompts, caminhos ou raw selection. Contexto e claims completos continuam nos artefatos internos existentes.
- Proxy aceita somente a nova rota exata com o mesmo Host/Origin/header/body/métodos anteriores. Não habilitar CORS nem leitura de `.env`.
- Snapshot público v1 e cliente de Production permanecem intactos. A projeção pública v2 será outro contrato por allowlist; não publicar este documento interno diretamente.

## Execução e arquivos de teste

```bash
python3 scripts/verify_visual_contract.py
python3 -m unittest discover -s scripts -p 'test_visual_contract.py' -v
npm --prefix web-ui test -- src/components/visual-preparation-regressions.test.tsx
```

Fixtures válidas e inválidas são exemplos de contrato, não holdout editorial. O manifesto lista o erro esperado de cada documento inválido. A validação JSON usa draft-07; o gate stdlib implementa apenas o vocabulário usado aqui, rejeitando keywords desconhecidas. Uma expansão de schema requer atualizar ou substituir o gate, sem ignorar keywords silenciosamente.

As cinco regressões legadas são expected failures explícitos. Remover `.fails` após corrigir cada comportamento; sucesso inesperado torna o gate vermelho. Não contabilizá-las como bugs resolvidos.
