# Logos originais e orientação vertical

Ajuste sobre `230b8a983d5926e193e3df0a79c2174bf2402cf1`, na mesma versão local **18111**.

Retirado o filtro CSS que transformava as logos do gráfico em silhuetas brancas. Os PNGs originais são os mesmos, sem placa branca, recoloração ou novos arquivos de imagem.

A identificação do visitante fica **acima da curva**, com “em vantagem / Acima do zero”. A do mandante fica **abaixo da curva**, com “em vantagem / Abaixo do zero”. Ambas estão alinhadas com a área desenhada. No exemplo CIN × BAL, Bengals ficam acima e Ravens abaixo, com suas logos coloridas. Essas identificações ficam fora da área de rolagem para continuarem visíveis ao ampliar o gráfico.

[Captura desktop](evidence/logo-axes/desktop-1440.png) · [Painel de 532 px](evidence/logo-axes/panel-532.png) · [Medições](evidence/logo-axes/layouts.json).

Conferidos 1440/390/320 px com fonte raiz 16/32 px: ambas as imagens carregadas, filtro `none`, visitante acima e mandante abaixo da área do gráfico, sem overflow da página. As configurações temporárias de viewport/fonte foram restauradas.

Passaram os **19 testes pertinentes existentes**, TypeScript, lint sem erros (um aviso herdado) e o build da entrada. Sem testes novos para esta alteração de apresentação. Fonte, pins, curvas, coordenadas, seleção de eventos, sequência recolhida e dados preservados. Hashes públicos mantidos; [isolamento](checks/logo-axes-isolation.json). Os logs `checks/logo-axes-*.log` registram a conferência.

Servidor próprio permanece **127.0.0.1:18111 / PID 83042**. Não houve merge, push, deploy ou nova avaliação humana nesta correção.
