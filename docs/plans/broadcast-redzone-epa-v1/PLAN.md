# EPA nas jogadas da red zone · plano anterior à implementação

Base: `e5c36cee30813cb882536114f401e5bc34d5c754`, referência 18107 preservada. Entrega local optativa, em 18108, sem publicação.

## Definição e apresentação

Nova população `classified-scrimmage-redzone-start-v1`: reutilizar `classified-scrimmage-v1`, restringindo a posição observada **antes** da jogada a `0 < yardline_100 <= 20`. Passe inclui sacks; corrida inclui scrambles. Field goals, punts, ajoelhadas, spikes, anuladas e tentativas especiais ficam fora. Jogada que parte de fora e termina dentro não entra; jogada que parte dentro e termina fora entra.

EPA/jogada = soma exata dos EPA finitos / número de jogadas elegíveis com EPA finito. EPA ausente/não finito não vira zero. Essa unidade é distinta de campanha e do denominador de TD/campanha. Posição/flags desconhecidas impedem uma média que aparente população definida. Sem oportunidades, fonte ausente e insuficiência ficam separados. Média zero válida continua zero.

Fonte: cópia física do pacote W1–2 pinado, com validação pelo leitor existente. Novo contrato/pin e reprodução; nenhum documento antigo é regravado. Reconciliação independente lê o Parquet com filtro separado e compara unidades, somas, denominadores e agregados. Agregado W1–2 soma e une jogadas únicas, nunca médias semanais.

No bloco red zone, depois das campanhas: título, dois resultados com EPA/jogada e quantidade de jogadas, escala comum assinada, uma frase diferenciando unidades. Regra, soma exata e jogadas ficam em detalhes. Sem seletores adicionais. Nas páginas de time: produção própria e dos adversários contra o time em W1–2. Não acrescentar ranking de EPA, modelo, previsão ou laboratório QB.

Preservar ardósia (#18232B), painel (#D6E1E6), texto (#15232C), Archivo e Roboto Condensed; reutilizar a escala assinada existente. A hierarquia mantém TD/campanha como leitura principal e EPA como leitura complementar. A aplicação antiga recebe um slot optativo com contexto default desativado.

## Verificação

Testes de fronteira de 20 jardas, exclusões, sacks/scrambles, EPA zero/ausente/não finito, ambiguidade, duplicatas, fonte ausente, agregação e adulteração. Prova dos 64 ataques e 64 agregados, HTTP exato, negativa de transporte, falha de fonte independente. Frontend, lint, tipos/builds afetados e isolamento público. Navegador 1440/390/320, teclado e texto ampliado; não declarar estudo humano.
