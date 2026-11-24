# Tipografia, temas e biblioteca inicial

## Fontes efetivamente utilizadas

Prova funcional: `/broadcast/type-proof.html`. Mesmo conteúdo, largura, tamanhos e superfícies claras/escuras para as duas candidatas. Recomendação: **Barlow**. Condensed Bold dá presença aos nomes sem compressão artificial; Semi Condensed Semibold organiza títulos; Barlow regular/semibold/bold atende contexto, controles e números. Plex permanece disponível para revisão, com caráter mais técnico e maior largura. Nenhuma candidata foi identificada como fonte da ESPN.

| Família | Cortes locais | Repositório oficial e revisão imutável |
| --- | --- | --- |
| Barlow | Regular 400, Semibold 600, Bold 700 | https://github.com/jpt/barlow/tree/dc2940e2e04ef4ec96c07e23e0f02aefbddd343b |
| Barlow Semi Condensed | Semibold 600 | mesma revisão |
| Barlow Condensed | Bold 700 | mesma revisão |
| IBM Plex Sans | Regular 400, Bold 700 | https://github.com/IBM/plex/tree/71f558992315a12ca1f06a2215d57962a1992162 |
| IBM Plex Sans Condensed | Bold 700 | mesma revisão |

WOFF2 completos, sem instalação global ou serviço externo em runtime. Versão registrada por commit oficial e SHA-256 de cada arquivo em `asset-files.json`. Licenças OFL preservadas junto aos arquivos (Barlow-OFL.txt e IBM-Plex-LICENSE.txt). O piloto solicita apenas as faces Barlow usadas; Plex é carregada na prova. `font-display: swap`, fallback Arial/sans-serif e `font-synthesis: none`. Não usamos scaleX.

A prova conferiu sinais, vírgulas, percentual e acentos, incluindo texto de 14 px. `font-variant-numeric: tabular-nums lining-nums`. CDP confirmou fontes customizadas reais em títulos, números e texto, inclusive Plex (`evidence/proof-rendered-fonts.json`), não apenas a declaração CSS. Os oito arquivos chegaram a `loaded`. Com requisições de fontes retidas, o conteúdo permaneceu legível em fallback (`type-loading.jpg`, `font-loading.json`); após liberar a rede, as fontes foram restauradas. Botão de simulação permite repetir a comparação sem rede. O fallback altera as larguras; não prometemos ausência de qualquer deslocamento durante a troca.

## Temas locais

`web-ui/local-editorial/broadcast/themes.ts` contém papéis separados. O helper público `teamColors.ts` não foi alterado. Hex de identidade conferidos em registros publicados abaixo; são fontes secundárias, **não certificação de manual oficial vigente**. As superfícies derivadas são decisões do produto.

| Time | Cor publicada / fonte | Superfície final e texto | Logo / cenário |
| --- | --- | --- | --- |
| BAL | #241773, #9E7C0C — https://usteamcolors.com/baltimore-ravens-team-colors/ | roxo #241773 → #191044, texto #F2F4F6 | cabeça de corvo lateral, escala óptica 1,6; cenário #252133 |
| DAL | #002244, #869397 — https://coloropedia.com/dallas-cowboys-colors-team-logo/ | prata derivada #D0D6DC → #AEB9C3, texto navy #002244 | estrela, escala 1,08; cenário #202E3B |
| NE | #002244, #C60C30 — https://www.brandcolorcode.com/new-england-patriots | navy #002244 → #071726, texto #F2F4F6; filete vermelho | Flying Elvis lateral, escala 1,65; cenário #252B35 |

Contraste no extremo mais desfavorável dos degradês: texto principal 10,67:1, secundário 5,57:1, contexto 8,53:1, BAL 13,18:1, DAL 8,02:1, NE 14,51:1. Parcelas gráficas 3,11:1, também separadas por textura, linha e rótulos. Valores completos em `contrast.json`. Lima reservado à assinatura e foco; ação principal escura e controles selecionados com preenchimento e sublinhado. Cor de dado não declara vantagem.

## Inventário inicial de imagens

Os snapshots já referenciavam os PNGs ESPN 500×500. Essas mesmas variantes foram preservadas localmente, sem alterar snapshots: `https://a.espncdn.com/i/teamlogos/nfl/500/bal.png`, `dal.png`, `ne.png`. Caminhos e hashes em `asset-files.json`. Transparência e proporção original mantidas. Conteúdo óptico varia dentro do canvas; escala ajustada por time, sem espelhar. Fallback de erro mostra a sigla, testado pelo evento de erro do elemento; a área fica reservada enquanto carrega.

Não foi identificada licença aberta para esses logos; marcas pertencem aos respectivos titulares. Uso aqui é o protótipo editorial local já autorizado, não uma declaração de direitos para redistribuição/publicação. Não extraímos ativos das referências. Os logos identificam o clube, não atestam que uma versão específica foi usada em cada jogo histórico.

| Categoria | Disponível / qualidade / orientação | Lacuna e caminho concreto |
| --- | --- | --- |
| BAL logo | PNG local 500 px, corvo voltado à direita, suficiente para cabeçalho | obter arquivo vetorial e condições de publicação se necessário |
| DAL logo | PNG local 500 px, estrela frontal | mesma lacuna de licença/vetor |
| NE logo | PNG local 500 px, perfil à direita | mesma lacuna; https://www.patriots.com/press-room/history-logo-uniform documenta história visual; https://www.patriots.com/fans/downloads-social-profile oferece materiais de perfil |
| Capacetes BAL | nenhum ativo local utilizável com origem/licença de imagem resolvidas | loja oficial: https://shop.baltimoreravens.com/baltimore-ravens-home-office-and-school-helmets/t-14265799%2Bd-03885430-250272%2Bz-9-960792340 |
| Capacetes DAL | nenhum ativo local adequado | catálogo de fabricante/loja NFL como candidato: https://www.nflshop.com/riddell/br-127058%2Bz-97271103-2082802123 |
| Capacetes NE | nenhum ativo local adequado | loja oficial: https://proshop.patriots.com/new-england-patriots-riddell-retro-collection-speed-mini-helmet/p-245514843936526067%2Bz-96-559715564 |
| Retratos | nenhum retrato integrado | dependerá de licença editorial, identificação do atleta e vínculo temporal; nenhuma estatística inventada |

As páginas de capacetes são caminhos de levantamento, não uma biblioteca aprovada. Orientação, recorte, resolução original e licença de reprodução das fotografias **ainda não verificados**. Uma licença do produto colecionável não concede licença da fotografia. Não baixados nem usados. Biblioteca futura deve registrar `team`, `variant`, `validFrom/validTo`, `orientation`, `source`, `rights`, dimensões e hash. Capacete alternativo/retro exige vínculo à temporada e, se apresentado como factual, ao jogo. Não espelhar para resolver orientação. A falta desse ativo não bloqueou a composição com logo.
