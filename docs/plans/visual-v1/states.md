# Matriz de estados e aceite visual

Fixtures sintéticas: `contracts/visual-analysis/v1/fixtures/`. AAA/BBB são fictícios. Nenhuma fixture é produção ou geração v5 comprovada. Os antigos casos reservados já abertos não são um holdout novo.

| Fixture válida | O que precisa aparecer | O que não pode acontecer |
| --- | --- | --- |
| complete-matchup | Quatro encontros com sinais distintos e um destaque | Reduzir tudo a um vencedor |
| opportunity | Ataque e EPA permitido positivos; oportunidade localizada | Afirmar exploração garantida |
| opposition | Ataque positivo e permitido negativo, em lados opostos do zero | Descrever defesa como ruim por ter sinal negativo |
| attack-not-demonstrated | Ataque negativo apesar de defesa permitir positivo | Presumir ferramenta para explorar a defesa |
| both-negative | Dois sinais negativos, com semântica de defesa explícita | Barra de magnitude parecer qualidade ofensiva |
| variation | Semanas positivas/negativas distinguíveis | Suavização ou média apagar mudança de sinal |
| zero | Ponto em zero exato e série que também inclui positivo | Zero virar ausência ou vantagem |
| tiny-sign / negative-tiny-sign | Desigualdade preserva sinal abaixo da precisão textual | 0,000 falso ou linguagem de relevância prática |
| tie | Passe e corrida com igualdade de destaque | Desempate por valor, nome ou ordem |
| both-sides | Oportunidades dos dois ataques | Ocultar uma ou chamar de refutação |
| partial | Série existente e ausência da contraparte | Inventar valor zero do lado ausente |
| missing | Quatro posições vazias com mensagem factual | Gráfico vazio com score ou fallback histórico |
| historical | Temporada anterior visível no período | Tratar referência como forma atual |
| coverage-gap | Semanas 1 e 3 e limite de cobertura | Preencher semana 2 ou chamar lacuna de bye |
| two-weeks | Duas observações; restrição curta explícita | “Consistente”, “comprovado”, “crônico” |
| general-represented | Geral acessível, agrupado sem igualdade numérica | Descartar a auditoria ou criar uma claim extra |
| uneven-weeks | Semanas de ataque e defesa rotuladas separadamente | Reclassificar automaticamente como incomparável ou esconder discrepância |
| outlier | +1,060 visível na escala, demais pontos preservados | Cortar extremo, estimar talento verdadeiro ou tendência |
| independent-opportunity | Relação independente, distinta de contraponto direto | Rótulo “refutação” |

Estados de aplicação para E3 (não são dados analíticos e não pertencem ao schema): catálogo carregando/vazio; nenhum resultado selecionado; POST em andamento; erro de rede antes/depois de enviar; histórico indisponível; resposta antiga após trocar jogo; tentativa v3 sem visual; documento inválido; consulta visual com hash/identidade divergente. Nenhum desses estados dispara POST automático. Manter a análise anterior visível em erro recuperável, com indicação clara.

## Wireframe e decisões de layout

Fontes: `wireframe/index.html`, `style.css`, `app.js`. É um protótipo estático independente; não copiar seu JavaScript monolítico para o produto. A entrega E3 usará componentes React compartilhados.

```bash
# Sempre um diretório novo, fora do repositório servido:
python3 scripts/render_visual_wireframe.py /tmp/nfl-visual-preview-NOVO
python3 -m http.server 18084 --bind 127.0.0.1 --directory /tmp/nfl-visual-preview-NOVO
```

O renderizador valida as fixtures e materializa somente HTML/CSS/JS, dados sintéticos e proveniência. Sem fetch externo, banco, geração, credenciais ou serving da raiz do repo. O botão “Simular celular” é conveniência de layout; não substitui teste em viewport real.

- Desktop: dois cartões por linha, cabeçalho e leitura rápida acima; geral e mercado em detalhe.
- Mobile: uma coluna, mesma ordem e mesmos fatos, sem rolagem horizontal; seletores e ações com área de toque de 44 px.
- Gráfico: duas séries rotuladas; pontos por semana; zero e números visíveis; defesa indicada como EPA permitido.
- Ressalva principal nunca fica escondida em details. Tabela e definição expandem via teclado.
- O banner de dados sintéticos é próprio do estudo e não entra no produto integrado. Tokens de cores/espaçamento são referência inicial para E3, sem exigir pixel match.

## Avaliação posterior E4

Tarefas: identificar time/fundamento do destaque; localizar uma evidência; dizer a temporada/semanas; explicar a principal limitação; distinguir defesa negativa de ataque negativo; reconhecer ausência; explicar por que dois destaques não elegem vencedor.

Comparar texto atual e visual com a mesma tarefa e ordem contrabalançada. Meta de localizar achado + ressalva em 10–15 s é hipótese de design, não limiar estatístico. Registrar respostas/erros e distinguir inspeção interna de avaliação com pessoas externas. Não exigir revisão manual de cada análise futura.

O aceite E1 confirma contratos e funcionamento do wireframe. Compreensão do público, relevância editorial e validação contra resultados reais pertencem a E2/E3/E4, não estão comprovadas aqui.
