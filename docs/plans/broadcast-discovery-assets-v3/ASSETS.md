# Identidade visual dos 32 times

Inventário anterior à aquisição: [calendário e URLs originais](calendar-team-inventory.json). O calendário 2026 contém 272 jogos e 32 siglas literais: ARI, ATL, BAL, BUF, CAR, CHI, CIN, CLE, DAL, DEN, DET, GB, HOU, IND, JAX, KC, LA, LAC, LV, MIA, MIN, NE, NO, NYG, NYJ, PHI, PIT, SEA, SF, TB, TEN, WAS.

[Inventário individual completo](assets.json): identificação, URL, aquisição, dimensões, PNG, bytes, SHA-256, procedência e direitos. Reutilizados oito arquivos: DAL/NE/BAL do piloto, PIT/GB/CHI/KC/BUF do refinamento. Adquiridos exatamente 24 PNGs pelas URLs ESPN já presentes no snapshot, inclusive CAR 500-dark, LA lar.png e WAS wsh.png. As diferenças de apresentação não são aliases da matriz de relações. Nenhum snapshot foi editado.

O [catálogo nflverse documentado](https://nflreadr.nflverse.com/reference/load_teams.html) confirma a separação entre gráficos, nomes, URLs e cores. O runtime usa exclusivamente broadcast-real/identity.ts e imports de arquivos locais, sem importar fixtures ou métricas para identidade. LAR e WSH são termos adicionais de busca; as identidades literais LA e WAS continuam intactas.

As superfícies dos 29 times acrescentados são decisões de contraste do protótipo, sem alegar paleta oficial certificada. DAL, NE e BAL conservam cores, gradientes e escala óptica anteriores. LA/NYG/NYJ receberam uma base clara atrás do PNG após revisão do painel de evidência; não houve recoloração da marca. Transparência, orientação e canvas dos originais permanecem. Todas as imagens usam contain. O componente Logo reserva espaço, não emite img para fonte vazia e reinicia o estado de erro quando time ou URL mudam.

Procedência anterior: [piloto](../metrics/e5c-4.2/ASSETS.md), [manifesto anterior](../metrics/e5c-4.2/asset-files.json), [cinco PNGs do refinamento](../broadcast-experience-refinement-v2/ASSETS.md). Licenças Archivo/Roboto Condensed continuam junto às fontes originais; nenhum arquivo de fonte foi alterado ou adquirido.

As marcas pertencem aos respectivos titulares. URLs públicos não concedem licença aberta de redistribuição. Uso no protótipo local autorizado; esta entrega não publica nem declara direitos para publicação. [Próximo piloto de capacetes](HELMET-PILOT.md).
