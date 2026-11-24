# Capturas e inspeção visual

Capturas do navegador integrado, com viewport nativo para evitar diferença entre layout e superfície de captura. Overrides temporários de largura/fonte/rede foram removidos ao final. O toque foi emulado; não houve teste em aparelho físico.

- [Hub preservado](captures/hub-preserved.png): W1–7 disponível com as fontes locais da referência.
- [Abertura desktop](captures/desktop-opening.png): três perguntas, definição breve e cobertura.
- [Gráfico desktop](captures/desktop-chart.png): 52 pontos, identificação por hover, nomes próximos, valores negativos, médias e diagonal sem rótulos de quadrante.
- [Composição desktop](captures/desktop-composition.png): categorias e valores, com DES próprio.
- [Sensibilidades de Stroud](captures/desktop-sensitivity.png): quatro definições simultâneas, A fixo e suporte de B.
- [DES em 390 px](captures/composition-des-390.png): lançamento desenhado com explicação, volume e EPA.
- [Evidência DES em 390 px](captures/evidence-des-390.png): descrição e identidade estável da fonte.
- [Navegação em 320 px](captures/navigation-320.png): três leituras empilhadas, sem truncar perguntas.
- [Texto 200%, 320 px](captures/stafford-320-text200-metrics.png): ambas as médias, volumes e reflow; nenhuma coordenada inventada.
- [Região densa por teclado](captures/dense-keyboard-390.png): foco nos nomes individuais após ArrowDown.
- [Falha de índice](captures/failure-390.png): estado sem pontos/métricas anteriores; recuperação comprovada no recibo.
- [Ausência de oportunidade](captures/no-opportunity-desktop.png): Andy Dalton sem média B/sem ponto, acessível na lista. Capturada antes do refinamento de singular/plural, sem diferença numérica.

[Valores de cinco exemplos e coordenadas DOM](evidence/browser-cases.json) · [reconciliação DOM/pacote](evidence/browser-reconciliation.json) · [navegação/histórico/recarga](evidence/browser-navigation.json) · [reflow](evidence/browser-responsive.json) · [toque e rolagem](evidence/browser-touch.json) · [falha/recuperação](evidence/browser-recovery.json).

A primeira tentativa de testes de componente usou ambiente Node sem jsdom e falhou na configuração; a segunda identificou uma expectativa de teste que ignorava paginação. Ambos foram corrigidos, sem alterar os números para acomodar o teste. Os logs iniciais estão separados do `frontend.log` final. Capturas não substituem o aceite visual posterior.
