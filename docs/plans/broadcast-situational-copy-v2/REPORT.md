# Acabamento editorial das análises situacionais existentes

Disponível em **http://127.0.0.1:18099/**, com os mesmos dados e percurso da referência. Foram alterados somente `SituationalReading.tsx`, um auxiliar puro local de composição, seus testes e três linhas de CSS para largura/respiro da nota. O restante da implementação e os documentos anteriores permanecem byte a byte iguais.

## Base e observação anterior

Referência confirmada limpa em `d410cc5ad9749255b241797a0f8c91a273b6a560`, branch `codex/broadcast-situational-w12-v1`; servidor 18098/PID49375 ativo antes do trabalho. Nova worktree gerenciada isolada `broadcast-situational-copy-v2`, branch `codex/broadcast-situational-copy-v2`, criada desse commit. A porta 18099 estava livre. O plano foi registrado no commit `a4b223b` antes da implementação.

No navegador, foram observadas e capturadas as duas análises reais de NYJ/ataque/W1 em 18098 antes de editar. Terceiras mostravam 20,0%, 2/10 e a frase redundante “NYJ registrou 2 conversões em 10 terceiras elegíveis neste recorte.” Red zone mostrava 66,7%, 2/3 e a repetição equivalente. O contexto principal mencionava modelo EPA não identificado.

## Os três ajustes

| Ajuste | Antes | Depois |
| --- | --- | --- |
| Regras próximas do resultado | Elegibilidade e linha20/ajoelhadas dependiam do expansível | Nota secundária após percentual/razão, usando a fonte e a cor de legenda já existentes. Terceiras explicitam regras do projeto, passe/corrida elegíveis, exclusão de kneels/spikes/anuladas/abortadas, detalhes de faltas e caráter não oficial. Red zone explicita campanha, linha20 inclusiva e posição observada antes de ajoelhada. |
| Informação factual adicional | Frase repetia numerador/denominador | Terceiras descrevem uma faixa, suas tentativas e conversões, mantendo desconhecidas explícitas. Red zone descreve os desfechos além de TD, ou a campanha única/TD-only de forma factual. |
| Esporte e procedência | Menção a EPA junto do contexto principal | Jogos, oportunidades, ataque/defesa, completude e leitura descritiva continuam no conteúdo principal. Modelo EPA, conhecimento temporal e os quatro UNKNOWN ficam sob “Procedência e garantias”, dentro do mesmo expansível. Hashes, versões e limitações foram preservados. |

Notas exatas:

> Taxa pelas regras do projeto: tentativas elegíveis de passe e corrida, sem ajoelhadas, spikes ou jogadas anuladas ou abortadas. Exclusões e penalidades nos detalhes; não é uma estatística oficial da NFL.

> A unidade é a campanha, com a linha de 20 jardas incluída. Campanhas com posição observada na região antes de uma ajoelhada também podem entrar na amostra.

As notas reproduzem as [definições existentes](../broadcast-situational-w12-v1/DEFINITIONS.md), que não foram editadas. Não se alterou a interpretação de penalidades nem se incluiu ajoelhada na população de terceira. A nota de red zone fala da posição observada antes do evento e não inventa uma oportunidade para qualquer ajoelhada fora da região.

O expansível mantém o mesmo summary e comportamento nativo por teclado. Seus dois títulos internos apenas distinguem regras esportivas e procedência; não há novo controle nem navegação. A informação “modelo EPA não identificado” está preservada nos detalhes, com o esclarecimento de que essas famílias não usam EPA.

## Frases e fontes numéricas

Todas as fontes abaixo são campos do documento original já validado pelo mesmo reader. Não houve novo processamento, LLM, API externa ou motor editorial genérico.

| Documento e família | Frase resultante | Campos originais utilizados |
| --- | --- | --- |
| NYJ/off/1 · terceira | 5 das 10 tentativas exigiam 7 ou mais jardas; 1 dessas 5 foi convertida. | third.denominator=10; byDistance.long.denominator=5; .numerator=1 |
| NYJ/off/1 · red zone | Além dos 2 touchdowns ofensivos, 1 campanha terminou em field goal. | redZone.numerator=2; outcomes.FIELD_GOAL=1 |
| NYJ/def/1-2 · terceira | Nas tentativas do ataque adversário, 11 das 21 tentativas exigiam 7 ou mais jardas; 1 dessas 11 foi convertida. | third.denominator=21; byDistance.long.denominator=11; .numerator=1; perspective=def |
| NYJ/def/1-2 · red zone | Nas campanhas do ataque adversário, além dos 3 touchdowns ofensivos, 2 campanhas terminaram em field goal. | redZone.numerator=3; outcomes.FIELD_GOAL=2; perspective=def |
| MIN/off/2 · red zone | A única campanha terminou em field goal. | redZone.denominator=1; numerator=0; outcomes.FIELD_GOAL=1 |
| ATL/off/1 · red zone | Mensagem de fonte presente sem oportunidades mantida; Sem taxa, 0/0 | status=NO_OPPORTUNITIES; denominator=0; ratio=null |
| BAL W3 | Mensagem de ausência mantida; sem painel numérico nem síntese | resolução SOURCE_ABSENT existente |

Escolha da faixa: maior contagem de tentativas entre longa, média e curta; em empate, ordem fixa longa → média → curta. A frase não usa “mais frequente” nem afirma predominância isolada. Essa ordem serve somente à estabilidade da redação. Havendo distância desconhecida, seu volume e conversões são mencionados mesmo quando outra faixa é escolhida. Se todas forem desconhecidas, a frase descreve esse fato sem inventar jardas. Não se atribui causalidade à distância.

Red zone mantém separados FG, FG perdido/bloqueado, turnover, perda por descidas, punt, fim de tempo/jogo, TD do time que defendia a campanha e safety. A ordem é fixa, independente da ordem das chaves do JSON. “Touchdown do time que defendia a campanha” preserva o sentido de OPPONENT_TOUCHDOWN relativo ao ataque da campanha, inclusive na perspectiva de defesa. Campanha única e somente TD recebem descrição curta sem elogio ou qualificação. Um desfecho futuro desconhecido não recebe descrição inventada. Zero e insuficiência nunca recebem síntese de uma população parcial; a mensagem existente continua.

Casos sintéticos, somente nos testes: empate 4/4/4 seleciona longa sem alegação de predominância; 11 desconhecidas em 23 tentativas permanecem explícitas; somente desconhecidas não recebem faixa inventada; insuficiência retorna ausência de fato adicional. Os testes verificam pares numéricos, atribuição, desempate, imutabilidade e posição da procedência, sem snapshots completos de HTML.

## Preservação e isolamento

[Gate próprio](verify-preservation.py) · [Resultado](checks/preservation.json). Caminhos autorizados exatos: os quatro arquivos de apresentação/teste indicados e esta pasta de documentação. Todos os outros arquivos históricos são comparados à base byte a byte. Nenhum gate antigo foi alterado ou afrouxado.

- Gráficos DistanceChart/DriveChart e componente de aquisição/seleção SituationalReading comparados literalmente à base: idênticos. App, URL, busca, hub, resumo antigo, transporte, reader, validação e Python estão intactos.
- CSS original integralmente preservado. O acréscimo contém somente max-width/margin da nota; sem mudar fontes, cores, logos, controles ou escala dos gráficos. A nota usa o sit-caption existente, 14 px na fonte normal e 28 px no teste a 200%; nenhuma fonte foi reduzida para acomodá-la.
- 162 arquivos das duas recuperações, bundle aceito de 588 observações e pacote situacional/cópia verificada conferidos contra seus hashes anteriores: intactos. Não houve geração ou nova cópia de dados.
- Respostas HTTP situacionais de 18098 e 18099 comparadas integralmente entre si e com o JSON preservado: mesmos 192 documentos, contagens, razões, estados e garantias. Catálogo do resumo antigo também idêntico.
- Build público mantém JS `73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5` e CSS `2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d`.
- Referência limpa no HEAD exato e servidor 18098/PID49375 ainda ativo. Nenhum processo foi encerrado para liberar porta.

## Verificações e capturas

269 testes frontend passaram em 27 arquivos, incluindo 14 novos casos de apresentação e ensaio real, com os 192 documentos/384 contextos habilitados. As cinco expected-failure legadas permanecem idênticas. Lint e os quatro builds journey/real/experience/público passaram. [Logs](checks/). O fixture sintético inicial precisou ter seu envelope tipado completado; o compilador permaneceu inalterado e o build foi repetido.

Navegador integrado: antes/depois em NYJ nas duas famílias; mesmos valores, markup dos gráficos e dimensões/estado dos controles em 1440; defesa/agregado W1–2; reload e voltar/avançar com documento/frase correspondentes; MIN com uma campanha; ATL sem oportunidades; W3 sem números. Empate, desconhecidas, somente TD e insuficiência foram exercitados nos testes sintéticos identificados, sem colocar esses dados na aplicação.

Dez medições/capturas em 1440, 390, 320 e fonte raiz200%, incluindo o expansível aberto pelo teclado. Não houve overflow horizontal da página nem dos elementos situacionais inspecionados. Foco visível e Enter no summary foram conferidos; método e os quatro UNKNOWN permanecem acessíveis no mesmo expansível. Viewport/fonte temporários foram restaurados. Não se afirma teste em aparelho físico nem avaliação de compreensão humana.

[Antes terceiras](evidence/before-third-1440.png) · [Depois terceiras](evidence/after-third-1440.png) · [Antes red zone](evidence/before-redzone-1440.png) · [Depois red zone](evidence/after-redzone-1440.png) · [390](evidence/nyj-redzone-390.png) · [320](evidence/defense-inclusive-third-320.png) · [Texto200%](evidence/third-320-text200.png) · [Método/procedência teclado](evidence/method-320-text200.png) · [Registro](evidence/browser.json).

Servidor próprio: **PID64333**, `node scripts/journey-dev.mjs`, somente **127.0.0.1:18099**, strictPort. [URLs e comandos](README.md). HEAD final e estado da árvore são conferidos no chat, sem hash autorreferente neste relatório.

Entrega limitada aos três ajustes editoriais. Cálculos, definições, populações, fontes e limitações analíticas são os mesmos. Não houve redesign da organização, novos controles, exploração, métricas, modelos, ampliação de semanas, merge, push, deploy ou publicação. Aceite humano permanece para avaliação.
