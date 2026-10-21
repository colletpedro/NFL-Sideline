# Limites da referência e próxima fronteira

## Alcance atual

- Todos os dados continuam fictícios, isolados em `web-ui/broadcast-experience/fixtures.ts`. O aviso persistente é “Demonstração · dados simulados”. Não são jogos ocorridos, previsão ou análise publicada.
- As regras de síntese pertencem à simulação: mínimo de 10 jogadas por ataque, proximidade de até 0,010 EPA/jogada e 2 p.p. de sucesso, com precisão e precedência preservadas. Não representam significância estatística nem aprovação para observações reais.
- Os componentes não foram integrados ao consumidor real. Contratos, snapshots, laboratório, backend, ETL e publicação permanecem separados e intactos. A referência é código experimental mais documentação e capturas.
- O feedback favorável descrito pelo usuário e a revisão do orquestrador são antecedentes registrados no [README](README.md). Não equivalem a pesquisa com participantes, resultados de compreensão ou certificação de acessibilidade do produto inteiro. Não houve nova aprovação visual humana nesta rodada.
- Publicação, merge, push, deploy e integração de dados reais não fazem parte desta entrega.

## Pendências separadas do eixo

O eixo corrigido não apresenta colisões nos 16 casos normais medidos nem nos sete casos de texto a 200%. Em 320 px, a fonte raiz de 32 px expõe um overflow de página já existente na v3: o texto auxiliar “Jardas e número de jogadas.”, em `stats-title p`, herda `white-space: nowrap` e alcança largura de página de aproximadamente 362 px. A mesma medida foi reproduzida na v3; a correção do eixo não a introduziu. Essa regra permanece fora do escopo.

Com texto a 200%, o gráfico também conserva sua rolagem horizontal **local**, herdada de `.epa-plot { min-width: 16rem }` e `.efficiency-chart { overflow-x: auto }`. Os rótulos continuam separados, mas limites e valores podem exigir deslocamento dentro do gráfico. O overflow da página descrito acima é uma pendência distinta. [Medições e evidências](../../plans/broadcast-axis-baseline-v4/REPORT.md).

## Aplicar a apresentação a uma observação real — somente fronteira documental

Antes dessa integração, será necessário um adaptador explícito entre a observação autorizada e os dados de apresentação. Ele deverá receber contexto/proveniência e informar quais afirmações são elegíveis; o renderer não deve inventar comparações nem importar fixtures para preencher lacunas. Se o consumidor autoriza uma observação por vez, a comparação de dois ataques da demonstração não pode ser transportada automaticamente.

| Assunto | O que o adaptador e a política real precisarão garantir |
| --- | --- |
| Denominadores e períodos | Identificar temporada, janela, instante de referência, fundamento e amostra válida. Reconciliar contagens/somas e derivar médias ponderadas corretamente; não fazer média simples entre médias de amostras diferentes. |
| Definições | Confirmar quais jogadas entram em passe/corrida, sacks, exclusões, sucesso e cobertura. Distinguir produção ofensiva de valores permitidos pela defesa. |
| EPA positivo/negativo | A fonte deve oferecer métrica válida, cobertura adequada e denominador positivo. Precisão e sinal exibidos precisam sustentar a frase. |
| Maior média ou volume | Comparação autorizada, participantes e recortes comparáveis. Explicitar denominadores e limites; adotar critérios reais próprios, sem copiar os limiares sintéticos por padrão. |
| Divergência EPA/sucesso | Ambas as métricas válidas no mesmo recorte, com definição e denominador compatíveis. Frequência de sucesso não pode virar resultado geral do time. |
| Ausência, pré-jogo e histórico | Ausência difere de zero; nenhum fallback silencioso de período/temporada. Histórico só com referência explícita, sem apresentá-lo como desempenho de uma partida futura. |
| Limitações e garantias | Validar finitude, unidades, contagens e relações numéricas; rejeitar ou representar inconsistência honestamente. Separar fatos da fonte, comparações elegíveis e limitações conhecidas. Preservar rastreabilidade e testes de contrato. |

Essa fronteira exige validação com os contratos e regras do consumidor real em uma entrega própria. Nenhum adaptador, endpoint, contrato novo, biblioteca de componentes ou política editorial real foi implementado aqui.
