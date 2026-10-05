# Contrato interno de evidências e claims v3 / v4 / v5

A geração tática recebe jogo, cobertura, observações semanais e recortes recentes determinísticos. Mercado não participa do prompt ou hash tático. `ContextQuality.COMPLETE` indica cobertura dos dois times, não confiança nem suficiência da amostra.

## Evidências e recortes

A observação `tw:{season}:{week}:{team}:{metric}` preserva valor original, unidade, volume pertinente, origem e chave de `team_week_metrics`. O ID independe da ordem. Nulos não criam observações; registros repetidos idênticos contam uma vez e conflitos falham.

O construtor continua selecionando os últimos três registros elegíveis de **cada time**, anteriores à semana do jogo. As semanas dos dois times podem diferir. Não preenche lacunas, presume bye ou busca uma semana adicional para substituir uma métrica nula. O corte histórico/postseason não mudou.

`recent_windows` contém uma janela `rw:{season}:{team}:{metric}:{origin}:{weeks}` por métrica/origem/temporada, calculada sobre todas as observações dessa métrica no recorte selecionado. Cada janela informa:

- semanas efetivas, IDs das observações de origem e média;
- método de agregação e volume pertinente quando conhecido;
- mínimo e máximo das médias semanais, sem apresentá-los como intervalo de confiança;
- `missingMetricWeeks`: semanas representadas por outras métricas desse time em que esta métrica está ausente. Isso não detecta semanas inteiramente sem observações e não determina a razão da ausência.

`PLAY_WEIGHTED_MEAN` pondera médias por volumes positivos conhecidos, exclusivamente para métricas com denominador de jogadas totais correspondente. Se algum volume faltar, usa `MEAN_OF_WEEKLY_MEANS`, explicitamente apresentada como **média das médias semanais, sem ponderação por jogadas**. Passe, corrida e early downs nunca usam volume total como denominador específico. O valor derivado usa DECIMAL128; a apresentação arredonda EPA a três casas e taxas a uma casa percentual. Não há shrinkage, ajuste por adversário ou substituição por valores históricos na mesma janela.

A política de três registros foi preservada; não foi estatisticamente validada como janela ideal. As médias são descrições do recorte, não estimativas calibradas da força verdadeira do time.

## Claims e seções

O gerador devolve `contract_version: 3`, `thesis_team`, `verdict`, `claims` e `sections`. Cada claim contém `claim_id`, `type`, `subject`, `predicate`, `period`, `evidence_ids`, `role` e `thesis_id` para contrapontos. Toda claim é utilizada; uma claim pode ser referenciada em seções diferentes, mas não repetida dentro da mesma seção.

| Tipo | Relação verificável |
|---|---|
| OBSERVATION | RECORDED de uma observação semanal |
| COMPARISON | GREATER_THAN/LESS_THAN da mesma métrica, temporada, origem e semana |
| WINDOW_COMPARISON | GREATER_THAN/LESS_THAN de duas janelas completas da mesma métrica, temporada, origem e método de agregação; semanas podem diferir |
| MATCHUP | Ataque de um time e defesa adversária no mesmo fundamento: passe, corrida ou jogada geral |
| LIMITATION | Limitação verificável no contexto |

`evidence_ids` de WINDOW_COMPARISON e MATCHUP referencia IDs `rw` reconstruídos pelo servidor, nunca subconjuntos escolhidos pelo LLM. Uma janela incompleta por métrica continua descritível, com a ausência explicitada. Comparações direcionais respeitam a semântica da métrica; dropback rate não classifica eficiência. Success rate permitido pela defesa descreve sucesso do **ataque adversário**, não sucesso defensivo.

MATCHUP admite:

- **ATTACK_DEFENSE_PROFILE**, papel LIMITATION: descreve ambos os recortes sem afirmar vantagem ou capacidade de exploração. Permite conclusão inconclusiva mesmo quando há algum sinal favorável.
- **POSITIVE_EPA_CONVERGENCE**, papel SUPPORT/COUNTER, origem corrente: requer EPA ofensivo positivo e EPA permitido positivo em **cada** semana observada dos respectivos recortes, sem semanas com essa métrica ausente entre as semanas representadas do time. Zero é a referência da própria métrica EPA; não é média da liga nem limiar de qualidade. A claim significa uma oportunidade condicional descritiva, não defesa ruim em relação à liga, superioridade geral, exploração comprovada ou probabilidade de vitória. Uma única observação pode satisfazer a regra, mas sua quantidade aparece no texto; não se afirma persistência.

Uma média positiva com semana negativa ou zero não satisfaz a convergência. A regra de sinais é uma política editorial conservadora, não um modelo calibrado. Não se compara numericamente EPA ofensivo com EPA defensivo como se sua diferença fosse vantagem projetada.

O fator-chave seleciona uma claim central. A vantagem contém uma MATCHUP ou NO_MATCHUP_SUPPORT. Leve inclinação exige convergência válida do time da tese; inconclusivo continua permitido. Não se exige que a defesa do time da tese também seja superior à outra defesa. NO_MATCHUP_SUPPORT só pode negar a existência de convergência quando não há um par elegível para nenhum time.

O alerta contém comparação favorável ao outro time ou MATCHUP de convergência do adversário, em dados correntes, vinculada à claim central; alternativamente contém limitação factual. O veredito mantém a limitação e reproduz o contraponto quando ele existe, evitando apagá-lo ao concluir.

Limitações disponíveis: NO_DATA, PARTIAL_DATA, HISTORICAL_ONLY, SMALL_SAMPLE (ao menos um time com até duas semanas atuais e algum dado atual disponível), LIMITED_WINDOW, NO_MATCHUP_SUPPORT, UNEVEN_WINDOWS (times com semanas atuais diferentes), MIXED_SIGNALS (EPA positivo e negativo na mesma janela). Uma limitação não substitui evidência contrária quando tal evidência existe; a relevância da escolha continua sujeita à avaliação editorial.

## Validação, persistência e limites

O Java valida referências, períodos, predicados, comparações, fundamento ataque/defesa e papéis editoriais, e controla os quatro textos públicos. IDs inexistentes, comparações falsas ou relações incompatíveis impedem gravação de cache utilizável.

`editorial-claims-v3` separa a identidade das novas gerações das versões anteriores. O cache guarda o contexto (inclusive janelas e proveniência), hash, metadados existentes e somente os quatro textos em `response_text`. Claims, papéis, referências de seção e resposta bruta do Gemini continuam transitórios. Não há trilha persistente completa nem migration nesta entrega.

Caches legados e aprovações existentes permanecem legíveis. O snapshot segue `schemaVersion: 1` e não expõe evidências, janelas, claims ou prompts.

Testes offline cobrem semanas desencontradas, cobertura desigual, ponderação correta, falta de denominador, outliers que escondem sinais opostos, mistura temporal, duplicação/reordenação e integridade das claims. Eles verificam consistência mecânica; não demonstram seleção editorial relevante, veracidade da fonte ou qualidade da resposta do Gemini real. A restrição a fundamentos e sinais ainda deixa fora lesões, adversários, situação de jogo e mecanismos causais não presentes nos dados.


## Extensão v4 histórica: encontros sem tese de vencedor

A entrada tática permanece v3; somente o **documento de claims** muda para `contract_version: 4`.
O caminho Gemini continua v3 sem mudança de prompt, hash ou cache. A fachada de renderização valida
ambas as versões, com restrições próprias; v3 não aceita os papéis/predicados novos.

V4 exige `thesis_team: NONE` e `verdict: INCONCLUSIVE`. Aceita MATCHUP e LIMITATION, com papéis
`OPPORTUNITY` (somente POSITIVE_EPA_CONVERGENCE) ou `LIMITATION`. Não admite SUPPORT, COUNTER nem
`thesis_id`. Toda convergência ainda satisfaz os testes semânticos v3 e também a cobertura adequada v4
formalizada em [política local](local-rules-editorial.md): período atual, mesmas semanas recentes completas,
mesmo método e nenhuma ausência por métrica. Essas restrições valem para **qualquer seletor** v4.

O novo predicado MATCHUP `CONFLICTING_EPA_PROFILE`, papel LIMITATION, exige ao menos um EPA semanal
positivo e um negativo na união das duas janelas pareáveis do fundamento. Não ordena força, não compara
numericamente ataque com defesa e não afirma que ambos os recortes individualmente mudam de sinal.
`ATTACK_DEFENSE_PROFILE` continua disponível para descrever pares sem direção, inclusive incompletos ou
históricos, explicitados como tais.

As quatro seções continuam sendo arrays de IDs de claims:

- `fator_chave`: 1–6 encontros ou uma única limitação quando não há encontro escolhido. Vários encontros
  são apresentados como alternativas sem eleição de fundamento único.
- `vantagem_tatica`: mesmos IDs/ordem do fator-chave. Um encontro recebe detalhes; mais de um recebe
  resumo neutro de todos, sem escolher o maior EPA para detalhar.
- `alerta_vermelho`: 1–6 claims; todo encontro precisa de vínculo explícito com o fator-chave.
- `veredito`: 1–13 claims; exige limitação factual, todos os encontros do alerta e **todas as oportunidades
  elegíveis** dos seis confrontos, incluindo fundamentos gerais não escolhidos como principais.

`links` é um array de `{from, to, relation}`. `from` pertence ao alerta e `to` ao fator-chave:
`DIRECT_CONFLICT` exige CONFLICTING_EPA_PROFILE sobre exatamente as janelas de `to`; admite reutilizar a
mesma claim para explicitar sua contradição, sem inventar tese. `INDEPENDENT_OPPORTUNITY` exige convergência
corrente do outro time e é redigida como oportunidade independente, nunca refutação direta. Sem encontro
contrário sustentado, o alerta usa limitação factual. Claims sem uso, IDs repetidos, fatos duplicados com
IDs diferentes, links inválidos e oportunidades omitidas no veredito são rejeitados.

Observações duplicadas idênticas em v4 são deduplicadas; conflitos de valores para o mesmo ID falham.
V3 preserva sua rejeição anterior de duplicatas no contexto passado diretamente ao renderer. Nem o nome
nem a versão do seletor aparecem nas condições do validador. `ClaimValidator` separa validação semântica
obrigatória de `ClaimRenderer`, que preserva formatação e vocabulário controlados. A versão do renderer é
`controlled-claims-v4.0.0`; os quatro campos públicos e o snapshot `schemaVersion: 1` não mudam.

O comando, a interface neutra tipada, os artefatos persistentes e o protocolo de congelamento estão em
[Motor editorial local](local-rules-editorial.md). Artefatos locais não são análises aprovadas, publicação
ou evidência da qualidade do Gemini. O motor local não exige revisão humana para executar.


## Contrato v5: dimensões de sinal e relações sem autorreferência

Vigente para o seletor local 2.0.0. Entrada congelada permanece v3. V3 (Gemini) e v4 (documentos
históricos locais) continuam com suas próprias regras/renderizações; DIRECT_CONFLICT v4 não é
reinterpretado. O serviço Gemini permanece limitado a v3. V5 exige NONE / INCONCLUSIVE, que
significam **ausência de estimativa de vencedor**, sem afirmar equilíbrio do jogo.

### Documento e claims

Mantém `contract_version`, `thesis_team`, `verdict`, `claims`, `sections`, `links`. Acrescenta
`groupings` (opcional quando vazio). Todos os campos e enums são tipados; campos arbitrários em claims
não geram fatos públicos. Toda claim precisa ser usada, e cada seção rejeita referências duplicadas.

- MATCHUP / SIGNAL_PROFILE: duas janelas completas reconstruídas, ataque e defesa adversária no mesmo
  fundamento, origem e temporada. `signals` deve ser **exatamente** igual às dimensões calculadas pelo
  validador: `attack`/`defense` com `pattern`, `valuesVary`, `containsZero`, mais `relation`.
- Papel OPPORTUNITY somente para POSITIVE_CONVERGENCE com a cobertura adequada herdada de v4.
  Demais relações têm papel LIMITATION. Os períodos CURRENT/HISTORICAL devem corresponder às fontes.
- WINDOW_LIMITATION: claim separada, papel LIMITATION, com duas referências às mesmas janelas de um
  encontro principal; sem `signals` próprio. Predicado verificável escolhido por prioridade:
  COVERAGE_LIMIT, SIGN_VARIATION_LIMIT, SAMPLE_LIMIT ou LIMITED_SCOPE.
- LIMITATION: condição factual do contexto, período NONE, subject MATCHUP e nenhuma referência:
  NO_DATA, PARTIAL_DATA, HISTORICAL_ONLY, SMALL_SAMPLE, UNEVEN_WINDOWS ou LIMITED_WINDOW.

As condições completas dos padrões/relacionamentos, zeros e cobertura estão em
[política 2.0.0](local-rules-editorial.md). Padrões por lado, relação e limitações coexistem. Uma janela
incompleta pode mostrar variação real, mas não ganhar oportunidade por faltar uma semana.

### Relações

Toda claim não global do alerta precisa de link `{from, to, relation}`, com `from` no alerta e `to`
no fator-chave; `from != to`. Não se admite DIRECT_CONFLICT em v5.

| Relation | Condição |
|---|---|
| INTERNAL_LIMITATION | From é WINDOW_LIMITATION distinto de to, e tem exatamente as mesmas referências do MATCHUP principal. O predicado deve corresponder à condição real do recorte. |
| ADDITIONAL_RESTRICTION | From é outro MATCHUP fora dos principais, mesmo ataque, fundamento diferente, mesma origem/temporada, sem convergência, restringindo a generalização de uma convergência principal. |
| INDEPENDENT_OPPORTUNITY | From é MATCHUP fora dos principais com convergência válida do outro time; não representa refutação direta. |

Links repetidos, alvos fora do fator-chave, autorreferências, relações incompatíveis e mudanças falsas
de padrão são rejeitados para qualquer produtor. O renderer recebe apenas objetos resolvidos pelo
validador, nunca o JSON não validado de um seletor.

### Seções e inventário público

Fator-chave tem 1–6 encontros principais (ou uma limitação se nenhum par estiver disponível).
Vantagem usa os mesmos IDs/ordem, mas uma realização numérica compacta que conserva todas as medidas
principais. Alerta aceita até 12 claims distintas de restrição/evidência adicional. Veredito aceita
até 19 referências internas, incluindo principais, alerta e uma limitação global; a realização é uma
síntese por time/padrão e **não** uma frase por claim.

O validador exige que todo candidato pareável esteja representado por MATCHUP no inventário do veredito
ou por agrupamento explicitamente validado. `groupings` contém `{candidateId, representedBy, reason}`;
reason único `GENERAL_SAME_SIGNAL_AND_COVERAGE`. Somente o panorama não representado diretamente pode
ser agrupado, por específicos do mesmo ataque com as equivalências de sinal/cobertura definidas na
política. Referências `representedBy` apontam a claims de MATCHUP presentes no veredito. Omitir um
sinal distinto ou oportunidade do outro time sem equivalência é inválido.

Esse inventário preserva informação, sem transformar métricas correlacionadas em votos ou inferir
reconstrução do EPA geral. A auditoria conserva os seis candidatos integralmente, inclusive os sem par.

### Realização e auditoria

Renderer `controlled-claims-v5.0.2` preserva os quatro campos públicos. Empates mantêm números,
recortes e variação semanal pertinente. Avisos compartilhados só são agrupados quando os metadados
forem iguais. Valor não zero que arredondaria a zero recebe desigualdade explícita em torno de 0,0005,
um limite exclusivamente de **formatação**, sem efeito na semântica ou seleção. Quando uma extremidade
da faixa exige desigualdade, mínimo e máximo são apresentados separadamente e identificados.

A identidade do resultado inclui contexto, seletor 2.0.0, contrato 5 e renderer. Artefatos internos v3
(v2 nas avaliações históricas) são imutáveis e não mudam schemaVersion de snapshots, cache Gemini ou aprovações. Não há geração
externa, banco, modelos instalados ou revisão humana obrigatória no comando offline.


### Revisão de clareza e avaliação local

Renderer 5.0.1 explicita ataque e defesa adversária no veredito e descreve sinais semanais
sem inferir trajetória. Seletor 2.0.0 e contrato v5 não mudam; artefatos 5.0.0 e contratos anteriores
permanecem preservados. O censo, os denominadores e os comandos estão em [avaliação de cobertura](coverage-clarity-evaluation.md).
