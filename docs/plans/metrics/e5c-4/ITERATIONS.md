# Rodadas de refinamento

## 1 — estrutura
Inspeção real BAL ataque W1–2 em 1440×1000 e 390×844. Antes: números abaixo da primeira tela desktop, mobile sem assunto esportivo. Nova composição: amostra + par de métricas; técnica em detalhes. A primeira captura mostrou navegação de laboratório ainda muito alta e sigla duplicada. Corrigidos: modos movidos após a leitura, identificação única visível, controles recolhíveis. Exatidão em BigInt preservada. Evidências before-*, round1-*.

## 2 — leitura e interação
Inspecionados DAL defesa/passe W2, NE defesa/passe POST2025 e BAL W3 em 390 e 320. Defesa mantém sinal e nome permitido; 35 passes / 67 gerais em DAL; NE permanece referência histórica. Troca de temporada exibe aviso. Problemas: estado ausente dizia “amostra do arquivo” apesar de não haver observação; PBP abria a mensagem com jargão; singular de semana incorreto; proporção positiva muito pequena poderia aparentar zero na barra. Correções: estado sem registro de jogadas com período preservado, singular/plural, texto explícito no lugar de barra subpixel; escopos originais nos detalhes. Revisada a restauração: autoescolha apenas sem preferência anterior e com um único arquivo pronto; preferência removida não aciona default em recargas posteriores. Erro/carregamento conservam identificação do recorte. Evidências round2-*.

## 3 — acabamento e reflow
Inspeção de 1440, 1024, 390 e 320 px; ampliação de texto a 200% em 1024 px. Em 320 px, o EPA quebrava o último algarismo; a composição foi ajustada para manter o número inteiro. Em texto ampliado, o volume quebrava entre dígitos; consultas de contêiner reorganizam amostra e métricas conforme espaço tipográfico, sem diminuir o texto ampliado. Essa regra inicialmente empilhou demais a identidade no mobile: corrigido o flex apenas em contêiner estreito. A conferência final encontrou também a mensagem sem fonte comprimida pela regra da amostra numérica; aplicada exceção de layout para prosa e reinspecionado BAL W3 a 320 px (after-gap-320). Singular/plural, alinhamentos, contagens e contraste revistos nos casos reais. Defesa DAL W2 mantém distribuição separada da eficiência; NE POST permanece histórico. Evidências round3-*, text-200-1024 e after-*.

## Verificação após refinamento
Os 48 recortes foram percorridos por controles reais no navegador, com identidade conferida. Teclado abriu/fechou detalhes com foco visível. Recarga preservou NE; sessão antiga, transporte interrompido, seleção removida e cancelamento de requisição foram exercitados. Casos sintéticos foram servidos apenas por interceptação temporária do navegador, explicitamente identificados. Interceptações e emulações foram removidas; dados reais restaurados. Veja relatórios JSON em evidence/.

As imagens “antes” reproduzem a base exata com o mesmo catálogo real. A captura mobile inicial tinha altura incorreta por uma corrida de redimensionamento da ferramenta; foi substituída por captura estabilizada da base, sem modificar seus arquivos.
