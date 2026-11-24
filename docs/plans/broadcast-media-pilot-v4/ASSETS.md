# Procedência e qualidade

[Inventário completo](assets.json) e [linhas do roster consultado](roster-evidence.json). Datas de obtenção, URLs, dimensões reais, formato, alpha, bytes e SHA-256 por arquivo. O catálogo de runtime é idêntico ao inventário e contém também os 32 logos legados; arquivos e componente Logo anteriores preservados.

## Estado dos oito alvos

Todos encontrados, obtidos e tecnicamente validados: PNG decodificado, transparência original, hash e dimensões conferidos. **Nenhum dos oito tem autorização específica de redistribuição estabelecida.** Condições gerais estão documentadas; a permissão específica continua não verificada. São candidatos para avaliação local, separados de approvedForPublication, que permanece vazio. Não há ativo novo qualificado para publicação.

| Time | Capacete | Retrato | Vínculo comprovado |
|---|---|---|---|
| DAL | Authentic Speed, padrão do catálogo, 515×515 | Dak Prescott, 3400×2450 | roster 2026; GSIS 00-0033077; ESPN 2577417 |
| NE | Authentic Speed, padrão do catálogo, 515×515 | Hunter Henry, 3400×2450 | roster 2026; GSIS 00-0033090; ESPN 3046439 |
| BAL | Authentic Speed, padrão do catálogo, 515×515 | Derrick Henry, 3400×2450 | roster 2026; GSIS 00-0032764; ESPN 3043078 |
| IND | Authentic Speed, padrão do catálogo, 515×515 | DeForest Buckner, 3400×2450 | roster 2026; GSIS 00-0032378; ESPN 2971282 |

### Capacetes

As quatro páginas oficiais de produto, vinculadas individualmente no inventário, responderam 200 nesta sessão e identificam a família Authentic Full Size/Speed. Os quatro arquivos antigos 515Wx515H realmente medem 515×515, têm alpha, capacete inteiro e ângulo lateral em três quartos com máscara à direita. O catálogo também mostrou imagens 1200Wx1200H de outros ângulos; esses arquivos não foram obtidos nem tratados como resolução superior dos originais escolhidos.

Exibição: frame máximo de 250 CSS px no piloto, com padding interno de 12 px; 220 CSS px na galeria. Os 515 px atendem aproximadamente 2× nessa escala; em densidade maior não há promessa de detalhe adicional. Não foram ampliados ou anunciados como 1024 px. Sem espelhamento, recoloração, corte, limpeza de fundo ou imagem artificial. Diferenças discretas de modelo da máscara e contorno pertencem aos produtos fotografados; mesma família não significa equipamento idêntico entre clubes.

[Termos oficiais Riddell](https://content.riddell.com/terms-conditions/) atribuem os materiais à Riddell. A [política do pressroom](https://news.riddell.com/multimedia/usage), já documentada no plano anterior, não licencia automaticamente o catálogo varejista. Não foi obtida licença específica desses arquivos. Crédito de procedência adjacente na galeria e no piloto; não é apresentado como substituto de permissão. Variante padrão do catálogo não comprova variante usada em BAL × IND ou outro jogo.

### Retratos

O [dicionário nflverse](https://nflreadr.nflverse.com/articles/dictionary_rosters.html) documenta season, team, gsis_id, espn_id e headshot_url. A aquisição efetiva do [roster 2026](https://github.com/nflverse/nflverse-data/releases/download/rosters/roster_2026.csv) retornou 3.054 linhas. Seleção realizada **depois** de conferir as linhas e por GSIS + time literal + season=2026; não por suposição de quarterback/titular. As quatro URLs headshot_url retornaram PNG 3400×2450 da NFL.com. Não foram escolhidas fotos apenas por coincidência de nome.

Originais preservados, incluindo alpha e RGB invisível fora da silhueta. Não houve tratamentos no rosto/uniforme. Os quatro têm enquadramento frontal de cabeça e ombros, mas a escala natural da cabeça varia, especialmente em IND; contain preserva o canvas, sem corte para forçar equivalência. Cerca de 13,2 MB de originais de retrato são conservados; lazy loading e espaço reservado na galeria. Este custo é aceitável para inspeção loopback, não é recomendação de payload público. Galeria não oferece estatísticas individuais.

[Termos NFL.com](https://www.nfl.com/legal/terms/) consultados nesta sessão reservam direitos e limitam os usos permitidos; não estabelecemos autorização específica para redistribuir estes retratos. Licença de dados/metadados não licencia automaticamente fotografias apontadas por URLs. A autoria/data individual da foto não foram demonstradas. Roster não comprova presença em uma partida, amostra, titularidade ou aparência histórica. Nenhum retrato entra na abertura ou junto às métricas.

## Alternativas verificadas e limites

[Guia TheSportsDB](https://www.thesportsdb.com/docs_api_guide): V1 aceita a chave pública 123; V2 e funcionalidades adicionais têm regras próprias. Quatro consultas gratuitas efetivamente realizadas: searchteams Baltimore_Ravens, searchplayers Derrick_Henry, lookupplayer 34166557 e lookupequipment 134922. As duas buscas retornaram o time 134922 e o jogador 34166557; isso não prova cobertura geral dos demais endpoints. Equipamentos retornaram duas entradas de 2025, sem um conjunto qualificado de quatro capacetes.

[Condições TheSportsDB](https://www.thesportsdb.com/docs_terms_of_use.php), atualizadas em 17/09/2026, exigem conferir a licença exata e direitos de terceiros. O lookup do jogador indicou CreativeCommons=Yes e atribuição a Chipermc, CC BY-SA 4.0, curid=110285767. Conferimos a [fotografia original](https://commons.wikimedia.org/wiki/File:Derrick_Henry_2021_09-19.jpg): Titans, 19/09/2021, outro uniforme/período. Essa licença diz respeito à fotografia indicada; não comprova automaticamente a origem/licença de cada thumb/cutout devolvido. Não a substituímos pelo retrato associado a BAL/2026. Alternativa registrada como encontrada, contexto/licença do original consultados, **arquivo não obtido nem integrado**.

A [categoria Wikimedia de capacetes](https://commons.wikimedia.org/wiki/Category:American_football_helmets) também foi examinada: fotografias heterogêneas de museu, jogos e modelos diversos; não se verificou neste levantamento um conjunto DAL/NE/BAL/IND padrão Speed coerente com alpha. Não é uma alegação de inexistência global. Pesquisa mantida no escopo pequeno; nenhuma compra, assinatura ou mensagem a terceiros.

## O que falta para qualificar

Para cada um dos oito originais: permissão específica ou licença verificável cobrindo o uso pretendido, autoria/obrigações de crédito e eventuais tratamentos/redistribuição. Para retratos com finalidade histórica: data e vínculo visual da imagem com a temporada. Para afirmar variante do capacete ou participação em jogo: prova específica do jogo. Nenhuma dessas ausências foi substituída por inferência.
