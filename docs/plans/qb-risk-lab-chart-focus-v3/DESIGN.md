# Gráfico como peça principal

Base `dc43f02c4c00e36e7b069b6a7dd7b7040c9f1ee8`, preservada. A skill UI/UX Pro Max foi consultada para hover/foco/toque: ação principal por clique/toque, foco visível e alternativa que não dependa de hover. A identidade aprovada continua: ardósia, papel claro, Archivo/Roboto Condensed e logos existentes. Nenhuma nova biblioteca.

Período, escala e posição compartilham uma barra compacta. O gráfico ocupa a largura útil do conteúdo; os blocos selecionado/lista vêm abaixo. A projeção é retangular: um domínio numérico comum e projeções independentes em largura e altura. A reta liga (0,0) a (máximo,máximo); não precisa parecer uma linha de 45 graus. A área de dados tem altura entre 260 e 440 px, evitando crescer até a largura de um desktop.

Não há nomes, caixas de quantidade ou linhas-guia permanentes. Cada ponto conserva o identificador e as coordenadas; uma área de interação transparente amplia seu alvo. A busca por proximidade usa distância visual local, sem encadeamento ou soma. Clique seleciona o mais próximo; a prévia e a lista permitem escolher cada integrante, inclusive coincidências exatas. Todos os pontos continuam focáveis por teclado. Enter/Espaço selecionam; seta para baixo leva aos nomes próximos; Escape fecha a identificação.

Hover só altera estado efêmero local. Não altera URL, seleção ou pedidos de evidência. A prévia permanece acessível ao mover o cursor até ela. No desktop ela se posiciona dentro do painel, acima/abaixo do ponto conforme espaço. Em telas estreitas ou texto ampliado, aparece abaixo dos eixos: mantém o gráfico descoberto e permite ler nomes e valores. O usuário pode fechá-la sem limpar a seleção.

Direita, acima e igualdade têm explicações abertas, adaptadas a totais ou por 100. Os três números do resumo continuam totais do mesmo período, explicitamente nomeados. A orientação contextual não transforma maior expectativa horizontal em pior desempenho.

Links antigos com `group` recebem explicação e mantêm todos os nomes na lista. Um jogador válido simultâneo permanece selecionado. Não tentamos reconstruir membros de uma marca que dependia da largura da tela anterior.
