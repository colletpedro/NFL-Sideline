# Rodada curta de compreensão — preparada, ainda não realizada

Objetivo: identificar rapidamente quem ataca/defende, fundamento/período, achado/limitação, lacunas e ausência de previsão. Duração sugerida: 5–10 minutos; isso não é tempo observado. A hipótese de 10–15 segundos se refere apenas a localizar achado e limitação, não a completar todas as perguntas.

## Preparação

Reproduzir a API/laboratório conforme [relatório E4](REPORT.md). Para a condição textual isolada, servir somente o diretório selecionado, em uma porta livre própria:

```bash
python3 -m http.server 18086 --bind 127.0.0.1 --directory docs/plans/visual-v1/e4/human
```

As páginas não fazem requests externos nem mostram gráficos. Conteúdo do renderer congelado, sem resumo escrito pelo agente. [Manifesto](human/manifest.json). Visual: usar o laboratório real, recuperar a tentativa de mesma identidade pelo histórico. Não pedir ao participante para gerar durante uma tarefa cronometrada: deixar carregado antes de iniciar. Não mostrar respostas/gabaritos ou o outro formato antes de registrar a resposta. No textual, abrir diretamente a página isolada.

Registrar familiaridade com NFL, exposição anterior a estes casos, largura/dispositivo e ordem. Selecionar A/B alternadamente entre participantes; se houver apenas um, escolher uma ordem antes de começar e registrar a limitação. Não repetir o mesmo caso no outro formato nesta rodada curta.

| Caso conhecido | Ordem A | Ordem B | Página textual |
| --- | --- | --- | --- |
| BAL–DAL 2026/3 | Texto | Visual | http://127.0.0.1:18086/2026_03_BAL_DAL.html |
| CHI–BAL 2025/8 | Visual | Texto | http://127.0.0.1:18086/2025_08_CHI_BAL.html |
| NE–JAX 2026/3 | Texto | Visual | http://127.0.0.1:18086/2026_03_NE_JAX.html |

Se só você participar, resultados exploratórios ainda são úteis; não permitem estimar efeito de formato/ordem. O contêiner textual separado tem apresentação semelhante ao texto completo, mas não isola perfeitamente tipografia/layout. Registrar essa diferença. Nenhum caso é holdout editorial; exposição prévia do participante também importa.

## Perguntas iguais em cada condição

Sem ajuda, responder verbalmente ou por escrito:

1. Qual é o achado principal? Localize também a limitação principal. O facilitador pode medir separadamente os tempos dessas duas localizações; se não medir, deixar null.
2. Qual time está no ataque e qual está na defesa? Qual fundamento aparece no destaque?
3. Quais temporada e semanas sustentam esse achado? A semana do jogo é a semana observada?
4. Os sinais demonstram o quê? O que o recorte não permite concluir?
5. Faltam dados ou os times têm semanas diferentes? Mostre onde percebeu isso. Se nada indicar ausência, diga que não encontrou; não invente causa para uma lacuna.
6. Dá para escolher um vencedor contando destaques ou olhando a cor? Explique por quê.

Após registrar as respostas, permitir detalhe/tabela e perguntar onde buscaria evidência. Anotar se abrir detalhes alterou a interpretação, sem substituir silenciosamente a resposta inicial.

## Dois controles qualitativos adicionais

No modo **explicitamente sintético**:

- `opposition`: EPA permitido negativo significa defesa favorável ou desfavorável? Quem prevalece está determinado?
- `partial` e `zero`: ausência é o mesmo que zero? Qual evidência unilateral continua disponível?

Esses controles não têm condição textual de renderer comparável; não misturar seus tempos com a comparação dos casos reais.

## Registro

Copiar [formulário vazio](human-results-template.json) para um arquivo novo com participante anônimo. Preservar respostas literais, tempos realmente medidos, erros, hesitações e pedidos de ajuda. Deixar null onde não houver dado. Não adicionar aprovação editorial/publicação.

Separar: observação humana; interpretação do avaliador; verificação dos fatos no documento. Contar respostas por pergunta com denominador explícito; não transformar um participante em validação populacional ou medição da hipótese de 10–15 s. Não juntar esses resultados com inspeção interna do agente.

Estado atual: zero participantes, nenhum tempo e nenhuma resposta humana coletada.
