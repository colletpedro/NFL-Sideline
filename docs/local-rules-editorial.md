# Motor editorial local — regras 2.0.0 / claims v5

Seletor `local-descriptive-rules` **2.0.0**, contrato de saída **5**, renderer
`controlled-claims-v5.0.2`, artefato **3** no serviço/CLI atuais (v2 nas avaliações históricas). Entrada: contexto congelado v3.
A interface `ClaimSelector.select(AnalysisContext, EditorialParameters)` permanece neutra, sem
prompt, HTTP, mercado ou configuração de provedor. `ClaimSelection` continua tipada; cada candidatura
agora registra as dimensões de sinal, além de janelas, cobertura e decisões editoriais.

`ClaimValidator` despacha por versão e só produz objetos validados que o renderer pode consumir.
V5 aplica as mesmas condições a qualquer produtor; não verifica identidade de seletor para conceder
exceções. Gemini permanece no prompt/cache/contrato v3, com barreira explícita no serviço contra adoção
acidental de contratos locais. Não há download, instalação ou execução de modelo.

## Recortes e cobertura preservados

Continuam sendo enumerados seis candidatos antes da escolha: ataque de cada equipe × defesa adversária
em passe, corrida e jogada geral. `EvidenceWindow` é reconstruída integralmente a partir das observações;
agregações, denominadores, IDs, limites temporais e política de três registros não foram alterados.

- **Pareável:** ataque/defesa correspondentes disponíveis, mesma origem e temporada.
- **Completo por métrica:** sem `missingMetricWeeks` nas semanas representadas pelo time.
- **Recente completo:** na fase REG da temporada atual, semanas exatamente
  `max(1, semanaJogo - 3)..semanaJogo - 1`, nos dois lados. Não presume jogos, byes ou causa de lacunas.
- **Comparável para oportunidade:** mesmo conjunto de semanas e método de agregação.
- **Cobertura adequada:** todas as condições acima. Não é suficiência estatística. Uma/duas semanas no
  início da temporada podem satisfazer a cobertura; sua limitação continua explícita.

Passe/corrida não têm denominadores específicos e usam média das médias semanais, sem ponderação.
No panorama geral, volumes pertinentes positivos completos mantêm a ponderação existente; ausência de
qualquer volume mantém a média não ponderada. Não são inventados volumes nem preenchidas semanas.
A política de calendário pode se abster em byes/atrasos: isso impede que retirar uma semana negativa
converta um recorte incompleto em oportunidade. Contextos históricos não viram oportunidade atual.

## Dimensões de sinal

Cada candidato inclui `signals.attack`, `signals.defense` e `signals.relation`, independentemente de
`limitations`. Cada lado tem `pattern`, `valuesVary` (mínimo diferente do máximo original) e
`containsZero` (alguma observação **exatamente** zero). Todas as semanas da janela são consideradas.

| Pattern semanal | Condição mecânica |
|---|---|
| ALL_POSITIVE | Todos os valores > 0 |
| ALL_NEGATIVE | Todos os valores < 0 |
| MIXED_SIGNS | Existe valor > 0 e valor < 0; zeros podem coexistir |
| ZERO_ONLY | Todos iguais a zero |
| NONNEGATIVE_WITH_ZERO | Existe positivo e zero, sem negativo |
| NONPOSITIVE_WITH_ZERO | Existe negativo e zero, sem positivo |
| MISSING | Janela ausente |

`valuesVary` pode ser verdadeiro mesmo com todos os valores positivos. Variação de magnitude não é
mudança de sinal, e nenhuma delas autoriza rotular um time como instável/inconsistente.

| Relação entre janelas | Condição e interpretação autorizada |
|---|---|
| POSITIVE_CONVERGENCE | Ambos ALL_POSITIVE + cobertura adequada: sinais compatíveis com oportunidade localizada, sem exploração comprovada. |
| POSITIVE_COMPATIBILITY_ONLY | Ambos ALL_POSITIVE, sem cobertura adequada: sinais observados positivos, sem oportunidade atual autorizada. |
| FAVORABLE_ATTACK_AND_DEFENSE | Ataque ALL_POSITIVE, defesa ALL_NEGATIVE: indicadores favoráveis ao ataque **e** à defesa; não estabelece quem prevalece. |
| ATTACK_NOT_DEMONSTRATED | Ataque ALL_NEGATIVE, defesa ALL_POSITIVE: a defesa permitiu EPA positivo, mas o ataque não mostrou produção positiva para sustentar exploração. |
| BOTH_NEGATIVE | Ambos ALL_NEGATIVE: descreve produção ofensiva e EPA permitido negativos; não projeta resultado. |
| WEEKLY_SIGN_VARIATION | Par disponível não coberto acima e pelo menos um lado MIXED_SIGNS. A atribuição a ataque, defesa ou ambos permanece explícita. |
| ZERO_PROFILE | Par disponível restante, com zeros e sem mistura positiva/negativa. |
| UNAVAILABLE | Um lado ausente ou períodos incompatíveis. As dimensões observadas de cada lado continuam disponíveis. |

O novo `classification` é uma projeção resumida dessas dimensões (`OPPORTUNITY`,
`OPPOSING_FAVORABLE_SIGNS`, `UNDEMONSTRATED_ATTACK`, `WEEKLY_SIGN_VARIATION`, `ZERO_PROFILE`,
`NEGATIVE_PROFILE`, `PROFILE`, `INSUFFICIENT_OR_INCOMPATIBLE`). Não substitui as dimensões ou limitações.
A categoria ampla CONFLICTING é usada somente na compatibilidade histórica v4.

### Zero e apresentação numérica

O sinal é calculado com o BigDecimal original, sem epsilon ou limiar de relevância prática.
EPA normalmente usa três casas, HALF_UP, vírgula decimal e sinal explícito. Zero exato é `0,000 EPA`.
Se um valor não zero arredondaria a zero, o renderer apresenta `0 < EPA < 0,0005` ou
`-0,0005 < EPA < 0`. O limite 0,0005 deriva exclusivamente do arredondamento de três casas; **não**
participa da seleção/classificação nem é limiar esportivo. A regra vale também para extremos semanais.
Taxas não entram nesta seleção. Dropback rate continua sendo frequência, sem direção de qualidade.

## Seleção, vínculos e omissão editorial

A ordem categórica de mérito permanece: pares com cobertura adequada, senão pares atuais, senão
históricos; preferir passe/corrida adequados, senão panorama geral disponível, senão perfis específicos;
nessa categoria, oportunidades precedem outros perfis. Todos os empates finais são mantidos.
Não há score composto, desempate pelo maior EPA, mando, nome ou ordem de entrada. Ordenar nomes e
fundamentos serve apenas à apresentação. Nunca se calcula ataque menos defesa como vantagem.

### Alerta

Cada encontro principal recebe uma **claim distinta** `WINDOW_LIMITATION` com os mesmos IDs de janela,
vinculada por `INTERNAL_LIMITATION` ao encontro. A prioridade é:

1. `COVERAGE_LIMIT` se a cobertura não for adequada;
2. `SIGN_VARIATION_LIMIT` se houver MIXED_SIGNS em algum dos lados;
3. `SAMPLE_LIMIT` se houver no máximo duas semanas;
4. `LIMITED_SCOPE` para o limite de três semanas/ausência de ajuste por adversário.

O alerta explica a restrição: média não representa sinal presente em todas as semanas, recorte curto
não caracteriza padrão duradouro, períodos diferentes não descrevem conjuntamente o momento atual.
Não chama o encontro de seu próprio contraponto e não repete simplesmente sua classificação.
Limitações iguais podem ser agrupadas no texto, mantendo todos os vínculos no documento.

`ADDITIONAL_RESTRICTION` exige outro encontro pareável, outro fundamento do mesmo ataque, mesma origem
e temporada, com relação diferente de POSITIVE_CONVERGENCE, restringindo a extensão de uma oportunidade
principal para o ataque inteiro. Não é uma comparação numérica nem uma refutação causal. Semanas
podem diferir, mas são mostradas na evidência adicional.

`INDEPENDENT_OPPORTUNITY` exige convergência válida do outro time, fora dos encontros principais. É
uma oportunidade independente, sem alegação de refutar o fundamento principal. Autorreferência é
proibida para **todas** as relações v5. Não há obrigação de inventar contraponto esportivo: na ausência
de par, usa-se uma limitação verificável do contexto.

### Panorama geral

Todos os candidatos e evidências ficam integralmente na auditoria. Preservação interna não obriga
repetição textual. Todo par específico permanece representado no documento do veredito; o panorama:

- acrescenta informação se suas dimensões de sinal/cobertura não estiverem representadas por um
  fundamento específico do mesmo ataque, ou se for principal pela política de cobertura;
- apresenta ressalva quando não sustenta a extensão de uma oportunidade principal; fica no alerta
  quando satisfaz ADDITIONAL_RESTRICTION e sempre na síntese do veredito;
- só é omitido editorialmente se não for principal e existir específico do mesmo ataque com mesma
  relação, padrões de ataque/defesa, presença de zeros, origem, temporada, semanas e limitações de
  cobertura. O documento registra `GENERAL_SAME_SIGNAL_AND_COVERAGE`, candidato omitido e claims que o
  representam. O validador verifica cada correspondência e exige cobertura de todo o inventário pareável.

Essa equivalência é **semântica**, não numérica. Diferenças de magnitude, variação de magnitude dentro
do mesmo padrão de sinais e volumes específicos não são novas direções; continuam na auditoria.
Na checagem de redundância, `WEEKLY_VARIATION` de magnitude e `UNAVAILABLE_DENOMINATORS` não são
comparados entre métricas com denominadores diferentes. Limitações como períodos, métrica ausente,
semanas diferentes e métodos incompatíveis **dentro do par** impedem agrupamento se divergirem.
Não se reconstrói EPA geral a partir de passe/corrida nem se contam os fundamentos como votos.
Oportunidade do outro time ou sinal contrário distinto não pode desaparecer por compactação.

## Responsabilidades públicas

- **fator_chave:** síntese curta dos aspectos principais; fundamentos com a mesma interpretação para
  o mesmo ataque podem compartilhar frase. Sem menção a desempate, algoritmo ou procedimento interno.
- **vantagem_tatica:** todos os encontros principais, inclusive empates, recebem médias ofensiva e
  defensiva, times, fundamento, semanas/temporada, contagem, extremos se houver variação e ausências por
  métrica. Períodos/agregações/explanações idênticos podem ser compartilhados uma vez. Períodos diferentes
  ficam junto de cada medida. Volumes ponderados aparecem junto das respectivas médias. Linhas separam
  encontros; não há texto livre fora dos templates/claims.
- **alerta_vermelho:** restrição interpretativa apoiada em claim própria ou evidência adicional. Não
  copia a manchete/descrição numérica principal. Evidência adicional tem seus próprios números/recortes.
- **veredito:** síntese por time e dimensão de sinal, com restrições e agrupamentos semanticamente
  verificados. Não enumera os IDs de claims nem repete panorama redundante. Afirma que a análise
  descritiva **não estima o vencedor**. INCONCLUSIVE/NONE é uma restrição de escopo, não evidência de
  equilíbrio, 50/50 ou indecidibilidade estatística.

## Execução offline e artefatos

Da raiz, sem carregar `.env`, com o Java 21 instalado nesta máquina:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
mvn -f core-api/pom.xml -o clean verify
java -jar core-api/target/core-api-0.1.0.jar editorial-local \
  editorial/evaluations/2026-09-26/contexts/2026_03_BAL_DAL.json \
  editorial/local-rules-v2/exemplo-novo
```

Em outra máquina, ajustar JAVA_HOME. O pai do destino deve existir; o destino precisa ser novo.
Sem Spring, banco, rede, cache ou revisão humana obrigatória. Caminhos públicos/symlinks correspondentes
são recusados. Cada tentativa, inclusive rejeitada, é imutável; retorno 0 validado, 1 rejeitado.

- `context.json`: projeção tática normalizada/deduplicada, janelas reconstruídas, sem campos arbitrários.
- `selection.json`: seis candidatos com dimensões, cobertura e janelas; motivos categóricos, decisões
  de agrupamento/omissão, documento completo de claims, relações e groupings.
- `claims.json`: documento v5 para validação independente da identidade do seletor.
- `rendered.json`: somente os quatro campos públicos, em artefato **interno**.
- `result.json`: artefato v2, hash da entrada/contexto, jogo, seletor 2.0.0, contrato 5, renderer v5.0.0,
  identidade do resultado derivada de contexto + todas essas versões, status/falhas sanitizadas.

Não há integração com cache; uma futura integração deve incluir essa identidade/versionamento.
Nenhuma análise aprovada, dado público ou publicação é alterada pela geração.

## Compatibilidade e regressão

V3 continua validado/renderizado pelo caminho anterior. Documentos v4 preservam suas regras antigas,
inclusive DIRECT_CONFLICT e sua autorreferência histórica; não são reinterpretados como relações v5.
Seis documentos v4 preservados têm teste de equivalência exata do JSON renderizado. `LegacyLocalRuleSelector`
permanece para testes/reprodução interna, sem ser o default da CLI. O protocolo antigo de avaliação não
pode ser usado para rotular a nova versão como holdout; o script histórico recusa versões posteriores.

A versão 1.0.0 e o congelamento em `editorial/local-rules-runs` não são sobrescritos. A política anterior
está preservada em `editorial/local-rules-v2/baseline-code/local-rules-editorial.md`.

```bash
python3 scripts/compare_local_rules.py editorial/local-rules-v2/comparacao-nova
```

Esse comando executa **todos os seis casos conhecidos** do manifesto original, incluindo SEA–WAS e
MIN–TB, como regressão; compara com os artefatos imutáveis 1.0.0 e gera quatro fixtures sintéticas por
condições de sinal. Não seleciona casos por resultado. Salva comparação estruturada, antes/depois dos
quatro campos, dimensões, números principais introduzidos, agrupamentos e exemplos completos.
As ocorrências de números na comparação são verificações textuais auxiliares, não prova de atribuição;
os testes Java conferem a ligação semântica. Não é nova avaliação independente nem evidência Gemini.

## Limites

Persistem a cobertura conservadora de calendário, denominadores específicos ausentes, falta de ajuste
por adversário, shrinkage, tracking, lesões e contexto causal. Variação semanal não permite concluir
instabilidade. Oposição de sinais não prevê qual unidade prevalece. O renderer pode ficar extenso quando
muitos recortes diferentes precisam ser explicitados; concisão não autoriza apagar evidência.
Não há probabilidades, confiança, scores ou thresholds de favoritismo.

Os testes verificam fatos, invariâncias e integridade da representação. Os seis casos já conhecidos e
as fixtures não comprovam qualidade editorial nem generalização. Uma avaliação independente requer
novos casos ainda não usados no ajuste, selecionados por protocolo próprio. Sua ausência não bloqueia
esta implementação e nenhuma revisão humana é exigida tecnicamente para gerar.

Divergências anteriores continuam registradas na política 1.0.0: a versão histórica de AGENTS.md descrevia `metricas_citadas`
embora o código já usasse claims v3; o cabeçalho antigo de Spec.md divergia da seção 7. Nesta entrega,
a documentação v4 passa a ser explicitamente histórica; nenhuma alteração implica migração pública.


### Revisão de clareza e avaliação local

Renderer 5.0.1 explicita ataque e defesa adversária no veredito e descreve sinais semanais
sem inferir trajetória. Seletor 2.0.0 e contrato v5 não mudam; artefatos 5.0.0 e contratos anteriores
permanecem preservados. O censo, os denominadores e os comandos estão em [avaliação de cobertura](coverage-clarity-evaluation.md).

### Faixas próximas de zero e validação operacional

Renderer 5.0.2 identifica mínimo e máximo quando um extremo exige desigualdade, por exemplo
`faixa semanal: mínimo (0 < EPA < 0,0005); máximo (+0,116 EPA)`. Faixas cujos extremos são
representáveis continuam em `x a y`. O limite é de exibição; seleção, sinais e valores não mudam.
HTTP real, persistência após reinício e apresentação em 1440/390 px foram verificados nos 21 casos
conhecidos. Isso não é avaliação independente. Evidências: [validação operacional](../editorial/operational-validation-v1/REPORT.md).
