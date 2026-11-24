# Motor editorial local 2.0.0 — entrega validada

## Implementação

Seletor **local-descriptive-rules 2.0.0**, claims **v5**, renderer **controlled-claims-v5.0.0**, artefatos
internos **v2**. Interface neutra de seleção preservada; validação e renderização permanecem separadas.
Todos os documentos locais novos continuam INCONCLUSIVE / NONE. O texto esclarece que a análise não
estima o vencedor, sem transformar a abstenção em uma conclusão sobre equilíbrio do jogo.

As dimensões registram separadamente padrões/variação/zeros do ataque e da defesa, relação entre eles
e limitações de cobertura. Os mesmos seis encontros são examinados; os recortes, agregações e requisitos
de cobertura para oportunidade não mudaram. Documentação: [política](../../docs/local-rules-editorial.md),
[contrato](../../docs/analysis-claims-contract.md), [Spec](../../Spec.md).

## Critérios mecânicos e relações

| Evidência | Interpretação autorizada |
|---|---|
| Ataque tem semanas positivas e negativas | Variação de sinal **no ataque**, independente da defesa. |
| Defesa tem EPA permitido positivo e negativo | Variação de sinal **na defesa**, independente do ataque. |
| Ataque sempre positivo / defesa sempre negativa | Indicadores favoráveis a ambos; não se sabe quem prevalecerá. |
| Ataque sempre negativo / defesa sempre positiva | A defesa permitiu produção positiva, mas o ataque não a demonstrou; sem alegar exploração. |
| Ambos sempre positivos, cobertura adequada | Compatibilidade descritiva com oportunidade localizada. |
| Ambos negativos, zeros ou cobertura insuficiente | Perfis/limitações explícitos, sem converter ausência em suporte. |

Os padrões usam valores originais, sem epsilon. Variação de magnitude entre semanas é armazenada
separadamente de mudança de sinal. Valores não zero que arredondariam a zero são exibidos como
`0 < EPA < 0,0005` ou `-0,0005 < EPA < 0`; zero exato é `0,000 EPA`. O limite é de formatação,
não relevância prática. Médias não são subtraídas para calcular vantagem.

O alerta agora tem claims próprias WINDOW_LIMITATION com evidências e ligação INTERNAL_LIMITATION
à principal, sem self-link. ADDITIONAL_RESTRICTION representa outro fundamento que restringe estender
uma convergência principal ao ataque inteiro; INDEPENDENT_OPPORTUNITY representa oportunidade do outro
time. O validador rejeita autorreferências, dimensões falsas e omissões sem justificativa verificável.

Os empates mantêm todas as médias, times, fundamentos e semanas no bloco vantagem. Agregação/período
iguais são apresentados uma vez; faixas semanais aparecem quando há variação. O veredito agrupa por
time e sinais, sem listar novamente cada claim. Panorama geral não principal só é omitido se um
específico do mesmo ataque já representa os mesmos padrões/zeros/origem/temporada/semanas/cobertura.
A equivalência é semântica: não afirma que EPA geral seja reconstruível ou numericamente equivalente.
Todos os candidatos ficam na auditoria, e sinais distintos não podem desaparecer na compactação.

## Reprodução

Da raiz, sem `.env`, usando um destino novo:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
mvn -f core-api/pom.xml -o clean verify
java -jar core-api/target/core-api-0.1.0.jar editorial-local \
  editorial/evaluations/2026-09-26/contexts/2026_03_BAL_DAL.json \
  editorial/local-rules-v2/exemplo-novo
```

Para reproduzir a comparação completa, igualmente em diretório novo:

```bash
python3 scripts/compare_local_rules.py editorial/local-rules-v2/comparacao-nova
```

O pai do destino precisa existir. Tentativas nunca são sobrescritas; caminhos públicos são proibidos.
O comando não inicia Spring, não usa cache/banco/rede/modelo e não exige revisão humana para gerar.

## Artefatos e comparação

A execução final é [regression-final](regression-final/). `regression-development` conserva a passagem
de desenvolvimento anterior aos últimos ajustes de agrupamento textual, sem sobrescrita.

- [Comparação integral antes/depois](regression-final/COMPARISON.md): classificações e quatro campos de
  cada um dos seis jogos, números principais introduzidos, omissões editoriais e informação preservada.
- [Comparação estruturada](regression-final/comparison.json): valores, relações, padrões e groupings.
- [Resultados](regression-final/results.json): seis casos reais conhecidos e quatro exemplos sintéticos.
- [Exemplos completos](regression-final/EXAMPLES.md): oposição, variação, empate real e oportunidades
  dos dois lados. Também reproduzidos abaixo neste relatório.
- Em cada caso: context.json, selection.json, claims.json, rendered.json, result.json. Há hashes,
  versões, dimensões, motivos, referências, vínculos e falhas sanitizadas quando aplicável.
- [Hashes desta versão](release-v2-hashes.json), [verificação](verification.json),
  [log Java 21](java21-clean-verify.log), [integridade do material preservado](preserved-input-hashes.json).

| Caso conhecido | Médias principais antes ausentes em vantagem e agora apresentadas | Panoramas agrupados |
|---|---:|---|
| 2026_03_ARI_SF | 8 | ARI:OFF_EPA_PLAY, SF:OFF_EPA_PLAY |
| 2026_03_BAL_DAL | 4 | BAL:OFF_EPA_PLAY, DAL:OFF_EPA_PLAY |
| 2026_03_NE_JAX | 8 | JAX:OFF_EPA_PLAY, NE:OFF_EPA_PLAY |
| 2025_08_CHI_BAL | 4 | nenhum |
| 2026_03_SEA_WAS | 0 | SEA:OFF_EPA_PLAY, WAS:OFF_EPA_PLAY |
| 2026_03_MIN_TB | 8 | MIN:OFF_EPA_PLAY, TB:OFF_EPA_PLAY |

A contagem é por medida/referência principal cuja apresentação no bloco vantagem foi verificada
textualmente; não significa fatos novos na fonte ou avaliação de qualidade. Os testes Java verificam
atribuição às evidências e semântica. No caso SEA–WAS, o alerta acrescenta a ressalva da corrida de SEA
com seus números, e o panorama redundante deixa de contar como mais uma oportunidade textual.

## Validação desta entrega

**Java 21.0.12.1, `mvn -f core-api/pom.xml -o clean verify`: 106 testes, zero falhas, zero erros,
zero ignorados.** São 11 testes adicionais: 10 de sinais/semântica/compatibilidade e 1 de isolamento
do contrato Gemini. A suíte v5 percorre 180 contextos sintéticos e suas transformações. As propriedades
anteriores também permanecem exercitadas na suíte histórica.

Cobertura: reordenação, duplicatas, troca de mando/times, mercado, remoção de dados, ausência de
veredito direcional, zeros/sub-resolução, variação independente, números nos empates, oportunidades
dos dois lados, agrupamento geral, preservação de ressalvas, rejeição de dimensões falsas/links de
si para si e omissões editoriais falsas. Seis documentos v4 preservados renderizam JSON idêntico ao
original. Serviço Gemini rejeita adoção implícita do contrato local. O script de avaliação histórico
recusa rotular a versão atual como novos reservados.

As dez gerações desta comparação foram validadas. `git diff --check` passou, assim como a verificação
de whitespace dos arquivos novos. **233 arquivos protegidos** (frontend/fontes públicas, artefatos
1.0.0, congelamento, avaliação anterior e manifesto de aprovação) foram conferidos por hash e não
mudaram. A geração não mudou frontend, análises aprovadas ou snapshots.

## Limites da avaliação e próximos pontos de investigação

Todos os seis jogos, inclusive SEA–WAS e MIN–TB, são agora **regressão conhecida**. Foram executados
todos, sem selecionar resultados favoráveis. As fixtures são sintéticas explícitas, definidas por
condições de sinal. **Não houve nova avaliação independente.** Isso não bloqueou a implementação;
uma avaliação de generalização requer casos ainda não usados no ajuste e protocolo separado.

A cobertura de semanas numéricas ainda pode se abster em byes/atrasos; faltam denominadores específicos,
ajuste por adversário e contexto causal. A saída continua maior em casos com vários recortes diferentes,
porque números, semanas e sinais contrários não são ocultados por concisão. Igualdade de padrões que
permite omitir panorama não demonstra equivalência numérica nem independência dos fundamentos.
Relevância editorial, facilidade de leitura e generalização ainda exigem avaliação própria.

Passar pelo validador comprova apenas consistência mecânica, **não qualidade editorial comprovada**.
Nada desta entrega avalia a qualidade do Gemini. Não houve geração externa, consumo de tentativas
Gemini, instalação/execução de modelos, acesso a banco remoto, commit, push, deploy ou publicação.
As mudanças anteriores no workspace foram preservadas.

---

# Exemplos completos — contrato v5

AAA e BBB são equipes fictícias; os exemplos sintéticos foram definidos por condições de sinal, sem seleção por resultado.

## Oposição ataque/defesa — sintético

**fator_chave**

Passe de AAA contra BBB: indicadores favoráveis ao ataque e à defesa.

**vantagem_tatica**

Temporada 2026, semanas 1, 2, 3 (3 observações por métrica). Médias das médias semanais, sem ponderação por jogadas.
Passe — AAA (ataque): +0,200 EPA; BBB (EPA permitido): -0,150 EPA. Ataque positivo e EPA permitido negativo em todas as semanas: indicadores favoráveis a ambos, sem estabelecer quem prevalecerá.

**alerta_vermelho**

Os recortes de passe de AAA cobrem até três semanas e não têm ajuste por adversário; não estabelecem uma característica permanente.

**veredito**

AAA — passe: indicadores favoráveis dos dois lados do encontro. A leitura se limita às semanas observadas. Esta análise descritiva não estima o vencedor.

## Variação semanal — sintético

**fator_chave**

Passe de AAA contra BBB: a leitura muda entre semanas observadas.

**vantagem_tatica**

Temporada 2026, semanas 1, 2, 3 (3 observações por métrica). Médias das médias semanais, sem ponderação por jogadas.
Passe — AAA (ataque): +0,167 EPA, faixa semanal de -0,100 EPA a +0,400 EPA; BBB (EPA permitido): +0,200 EPA, faixa semanal de +0,100 EPA a +0,300 EPA. Ataque: semanas positivas e negativas. Defesa, em EPA permitido: positivo em todas as semanas.

**alerta_vermelho**

As médias do ataque de AAA (passe) combinam semanas de sinais diferentes; não descrevem um sinal presente em todas elas.

**veredito**

AAA — passe: mudança de sinal no ataque; EPA permitido adversário positivo em todas as semanas. A leitura se limita às semanas observadas. Esta análise descritiva não estima o vencedor.

## Alternativas empatadas BAL–DAL — real, contexto congelado conhecido

**fator_chave**

Passe e Corrida de BAL contra DAL: sinais compatíveis com uma oportunidade localizada.

**vantagem_tatica**

Temporada 2026, semanas 1, 2 (2 observações por métrica). Médias das médias semanais, sem ponderação por jogadas.
Passe — BAL (ataque): +0,239 EPA, faixa semanal de +0,103 EPA a +0,376 EPA; DAL (EPA permitido): +0,371 EPA, faixa semanal de +0,035 EPA a +0,707 EPA.
Corrida — BAL (ataque): +0,208 EPA, faixa semanal de +0,136 EPA a +0,280 EPA; DAL (EPA permitido): +0,083 EPA, faixa semanal de +0,061 EPA a +0,106 EPA.
Em cada encontro descrito: O ataque produziu EPA positivo e a defesa permitiu EPA positivo em todas as semanas do recorte; a compatibilidade não demonstra exploração no jogo.

**alerta_vermelho**

Nos recortes de passe e corrida de BAL, há no máximo duas observações semanais por métrica; o recorte curto não estabelece um padrão duradouro.

**veredito**

BAL — passe e corrida: oportunidade localizada. DAL — passe: mudança de sinal no EPA permitido adversário; ataque positivo em todas as semanas; corrida: mudança de sinal no ataque e no EPA permitido adversário. A leitura se limita a um recorte curto. Esta análise descritiva não estima o vencedor.

## Oportunidades dos dois lados — sintético

**fator_chave**

Passe de AAA contra BBB: sinais compatíveis com uma oportunidade localizada. Corrida de BBB contra AAA: sinais compatíveis com uma oportunidade localizada.

**vantagem_tatica**

Temporada 2026, semanas 1, 2, 3 (3 observações por métrica). Médias das médias semanais, sem ponderação por jogadas.
Passe — AAA (ataque): +0,111 EPA; BBB (EPA permitido): +0,222 EPA.
Corrida — BBB (ataque): +0,333 EPA; AAA (EPA permitido): +0,444 EPA.
Em cada encontro descrito: O ataque produziu EPA positivo e a defesa permitiu EPA positivo em todas as semanas do recorte; a compatibilidade não demonstra exploração no jogo.

**alerta_vermelho**

Os recortes de passe de AAA e corrida de BBB cobrem até três semanas e não têm ajuste por adversário; não estabelecem uma característica permanente.

**veredito**

AAA — passe: oportunidade localizada. BBB — corrida: oportunidade localizada. A leitura se limita às semanas observadas. Esta análise descritiva não estima o vencedor.
