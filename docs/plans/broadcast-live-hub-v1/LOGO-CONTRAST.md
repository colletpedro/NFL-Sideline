# Correção de contraste das logos · 2026-10-23

Solicitação: substituir os quadrados claros por marcas brancas e transparentes sobre as cores dos times.

Giants, Jets e Rams já eram os três casos sinalizados no catálogo como necessitando contraste. Na experiência local, os fundos e o padding dessas placas foram retirados. Nos painéis coloridos, a marca recebe brightness(0) invert(1); em busca e demais áreas claras, preserva suas cores originais. Transparência, desenho, arquivos e identidades dos times não foram alterados. Nenhum download ou processamento de raster foi necessário.

A implementação usa três variáveis de apresentação no Logo compartilhado; seus valores padrão preservam o comportamento anterior fora da entrada journey. O CSS da entrada atual define a variante conforme o contexto, sem !important e sem selecionar arquivos por seus nomes. O gate passou a autorizar explicitamente esse único arquivo compartilhado adicional, conforme esta solicitação; todos os caminhos públicos e de dados continuam protegidos.

[Giants sem placa](evidence/logo-contrast/giants.png) · [Jets sem placa](evidence/logo-contrast/jets.png) · [Estilos computados dos três times e da busca](evidence/logo-contrast/contrast.json).

No navegador, LA/NYG/NYJ têm fundo rgba(0,0,0,0), padding 0 e filtro branco sobre as cores dos times. Na busca, fundo transparente, padding 0 e filtro none. Os três PNGs originais são RGBA e permanecem intactos.

Passaram 246 testes, lint, build local journey e build público. O gate de preservação e git diff --check passaram; os hashes públicos permanecem idênticos. Sem novas métricas, alterações de dados, merge, push ou deploy. Servidor mantido em http://127.0.0.1:18097/.
