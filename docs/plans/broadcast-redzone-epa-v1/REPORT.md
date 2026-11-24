# EPA na red zone · relatório

O novo painel complementa as campanhas nas 32 páginas de confronto e nas 32 páginas de time W1–2. Apresenta EPA/jogada dos dois ataques, ou produção própria/adversária no agregado, sem exigir seletores adicionais. O EPA principal do jogo/time e a taxa TD/campanha mantêm suas populações e valores.

## Definição e reconciliação

Contrato `broadcast-redzone-epa-v1`, regra `classified-scrimmage-redzone-start-v1`. Reutiliza o classificador existente `classified-scrimmage-v1` e acrescenta **posição anterior à jogada `0 < yardline_100 <= 20`**. Sacks e scrambles entram; chutes, punts, ajoelhadas, spikes, anuladas e tentativas especiais não entram. O desfecho da campanha não seleciona jogadas. A métrica não é EPA por campanha inteira.

Soma exata com `Fraction(str(Float64))`; denominador de jogadas com EPA finito. EPA ausente/não finito não vira zero; as contagens ficam explícitas. Flags/posição indeterminadas impedem uma média que aparente população definida. W1–2 usa soma e união de IDs únicos; componente ausente/insuficiente impede média do agregado. Comparação somente descritiva entre observações disponíveis com mesma definição, fonte e período. O novo pin identifica essa projeção; os pins antigos não foram reinterpretados como autorização da nova população.

O filtro independente em Polars, separado do projetor e classificador, leu os 5.489 registros do Parquet e reconciliou **580 jogadas, 64 produções por jogo e 64 perspectivas agregadas**: zero divergências em IDs/ordem, somas, médias ou denominadores. Das 64 produções por jogo, 62 têm média; ATL fica sem oportunidades nas duas semanas. Todos os 580 EPA selecionados são finitos no arquivo atual; estados incompletos foram verificados com casos controlados, sem introduzi-los no calendário.

| Recorte | Primeira produção | Segunda produção |
| --- | --- | --- |
| NE × SEA W1 | NE −0,913 · 2 jogadas | SEA −0,305 · 6 jogadas |
| NYJ × TEN W1 | NYJ +0,343 · 7 jogadas | TEN +0,752 · 3 jogadas |
| ATL × PIT W1 | ATL sem média · 0 jogadas | PIT −0,002 · 6 jogadas |
| NYJ W1–2 | NYJ +0,438 · 15 jogadas | Adversários +0,420 · 11 jogadas |

Percentuais de TD/campanha não usam esses denominadores. Por exemplo, NE e SEA continuam com duas campanhas cada, apesar de 2 e 6 jogadas com EPA válido.

## Interface e interação

Preservadas ardósia, painéis claros, Archivo/Roboto Condensed, links de identidade, classificação compacta e ícones das campanhas. O novo painel aparece dentro da red zone, após as campanhas, com resultados em destaque e escala comum assinada. Regra e jogadas originais ficam em detalhes, incluindo soma/média exatas e exclusões. Os rótulos mínimo/zero/máximo reutilizam a escala existente, ampliada conforme os valores. Não foi acrescentada classificação de EPA. Na revisão dos extremos, PIT −3,515 expôs colisão do zero com a borda positiva em 320 px. O zero passa para uma segunda linha quando fica próximo de uma extremidade, preservando a posição horizontal e todos os limites. Os extremos negativo (PIT–NE) e positivo (CLE–JAX) foram reconferidos com fonte de 16 e 32 px, sem colisões, em `evidence/extreme-axes.json`.

As duas alterações compartilhadas são slots com contexto default desativado em `w12/Charts.tsx` e `hub-team/TeamPage.tsx`; consumidores antigos continuam sem o painel. Entrada, contexto, transporte, CSS e projeção são isolados. Uma requisição pinada carrega o novo pacote; mudar de jogo usa a identidade correta na coleção, sem esperar respostas de outro jogo. A falha do EPA é independente das fontes existentes.

Inspeção em 1440, 390 e 320 px para NE–SEA, NYJ–TEN, ATL–PIT e NYJ agregado: sem overflow horizontal normal ou colisão nos eixos novos. Texto real ampliado por `Page.setFontSizes` de 16→32 px em 1440/390/320: painel novo contido e sem colisão de rótulos. Enter abre método e jogadas; Tab alcança a tabela com foco visível de 3 px. A tabela preserva rolagem horizontal local para a evidência extensa. Não foi alegado zoom por atalho nativo, toque físico ou avaliação humana.

**Limite herdado medido:** em 390 px com fonte raiz de 32 px, a porcentagem anterior `18,2%` das terceiras provoca largura de documento de 399 px. O mesmo valor e a mesma geometria foram reproduzidos na referência 18107. Não vem do painel EPA; a correção dessa composição anterior fica separada. A referência estava inativa na conferência e foi restaurada no mesmo HEAD, sem alteração de arquivos.

Capturas: [desktop](evidence/final-ne-sea-1440.png), [390](evidence/final-ne-sea-390.png), [320](evidence/final-ne-sea-320.png), [time](evidence/team-nyj-390.png), [ATL](evidence/atl-pit-390.png), [teclado](evidence/keyboard-units-390.png), [texto 200%](evidence/text200-320.png). Medições em `evidence/browser.json` e comparação herdada em `evidence/baseline-text200-overflow.json`.

## Transporte e preservação

Novo endpoint GET `/__redzone-epa/`, somente loopback na porta 18108, headers explícitos e pin da coleção. Query, body, host/origin incompatíveis, métodos e headers duplicados são recusados. O processo Python valida e recalcula o pacote; Vite congela bytes no início; o cliente verifica o SHA-256 e a coerência das médias/unidades/agregados. Não há path arbitrário recebido do navegador, proxy, requisição externa ou fallback de período/time.

**79 verificações HTTP**: novo payload byte a byte, negativas/409 e 64 documentos antigos mais seus dois índices byte a byte. Falha controlada usando configuração para fonte inexistente retornou 503 somente no novo endpoint; no navegador ficaram as quatro campanhas de NE–SEA e o EPA principal −0,110/+0,066, sem novos valores. A configuração normal foi restaurada e os valores corretos foram reconferidos. Evidências em `checks/source-absent-http.json` e `evidence/source-absent-browser.json`.

Pacote, cópia física e reprodução conferidos com **53 arquivos idênticos**. Fontes originais completas seguem dentro do pacote. Pin: `sha256:6e6bffd6d2e8fc1e70e9d47e395f250b8dcf2cbc084bedbf4e4a32fb2ccf8af6`.

## Verificação técnica

- **334 testes frontend**, incluindo nove novos; cinco falhas esperadas legadas preservadas.
- **31 testes novos Python**, incluindo fronteiras da linha de 20, destino versus início, exclusões, sacks/scrambles, zero, ausência/não finitos, ambiguidade, duplicatas, soma ponderada, leitor real, reprodução e adulterações com hashes externos recalculados. Mais 30 testes pertinentes dos pacotes de confronto/time: 61 casos únicos aprovados. Na primeira execução, quatro testes antigos estavam sem as variáveis de fonte; foram reexecutados explicitamente com os pacotes reais e todos passaram. Logs separados preservam essa distinção.
- Lint sem erros, com o aviso Fast Refresh já herdado de `reading-polish/main.tsx`.
- TypeScript da entrada/consumidores e da configuração; build novo e oito builds experimentais anteriores; build público normal e sob variáveis adversas aprovados.
- Hashes públicos JS/CSS idênticos à base. Snapshots, contratos antigos, SQL, Java, aquisição, processo semanal e dados públicos preservados. `git diff --check` aprovado.

Completude, cobertura esperada, modelo EPA e disponibilidade histórica continuam UNKNOWN. Valores descrevem somente esta amostra; uma ou duas jogadas não demonstram capacidade estável. Sem nova avaliação humana, modelo ML, atribuição por quarterback, novas semanas, publicação, merge, push ou deploy.
