# Estrutura e limites

Entrada `/?view=explorer`, somente no percurso local broadcast-journey. O build público e os outros dois protótipos permanecem independentes. App reutiliza carregamento do calendário; Explorer acrescenta uma aquisição do mesmo snapshot situacional congelado, no endpoint original e com o mesmo marcador. Não existe escolha de transporte via URL. A sessão antiga de 588 observações continua carregada pelo App, disponível no resumo. Não se duplica a aplicação.

A entrada anterior recebe um link explícito no caminho responsivo. O explorador tem retorno explícito e acesso ao resumo anterior. Troca de time/jogo usa os jogos disponíveis no calendário; perspectiva e período ficam visíveis em um único lugar. As três perguntas são atalhos diretos, sem etapas obrigatórias. No mobile os nomes curtos são “Por distância”, “Passe e corrida” e “Red zone”; o título do resultado identifica a pergunta completa.

Contexto compacto: time, perspectiva e jogo/semana. W1–2 é inclusivo e os dois jogos/adversários são explicitados no aprofundamento e nos recortes fixados. O jogo âncora continua identificado no contexto. Se o jogo âncora não tiver fonte, não se usa um período alternativo automaticamente.

## URL

- Dimensões originais: `season`, `week` de origem, `game`, `team`, `side`, `reading`, `analysis`. `q` e demais parâmetros da busca são conservados, inclusive quando o jogo ativo muda de W1 para W2.
- Estado novo: `view=explorer`, `question=distance|type|outcomes`, `refine` e memória opcional `refine-distance|refine-type|refine-outcomes` para retomar cada pergunta. Só a pergunta ativa aplica um refinamento; as memórias não são filtros cruzados.
- Até dois parâmetros repetidos `pin=documento~pergunta~refinamento~bundleId`. Exemplo: `NYJ/off/1~distance~long~sha256:2af2…`. O ID completo é escrito pela interface. Não há numerador, denominador ou taxa livre na URL.
- Recorte fixado é reconstituído somente se documento, pergunta/refinamento e identidade exata da fonte existirem na sessão validada. Fonte divergente, formato inválido, duplicação ou terceiro recorte produz erro explícito. Remover os pins inválidos é uma ação do usuário.
- Recarga, link direto e histórico reconstroem investigação e comparação. Estado visual dos expansíveis não é parte da investigação e volta fechado na recarga.
- Sem contexto, o exemplo NYJ/ataque/W1 é materializado com `replace` e rotulado “Exemplo inicial”. Valores explícitos inválidos não são substituídos. Na passagem do resumo para o explorador, a ação explícita remove as identidades nominais do resumo, que não identificam documentos situacionais, conservando as dimensões compatíveis.

## Projeções

| Pergunta | Refinamentos | Numerador e denominador |
| --- | --- | --- |
| Terceiras por distância | Todas; curta 1–3; média 4–6; longa 7+; desconhecida | Conversões / tentativas do mesmo `byDistance` (ou medida total) |
| Passe e corrida | Ambos; passe incluindo sacks; corrida incluindo scrambles | Conversões / tentativas do mesmo `byType`. Gráfico também mostra tentativas desse tipo / todas as tentativas, como a leitura anterior. |
| Desfechos de red zone | Todos e os desfechos nomeados no contrato | Contagem do desfecho / todas as campanhas confirmadas. “Todos” mostra TD / campanhas. Ao destacar, a taxa de TD original é explicitada. |

`byDistance` e `byType` são marginais distintas. Não existe seleção distância × tipo, nem “corridas em terceiras longas”. O refinamento único pertence à pergunta ativa. Red zone não filtra campanhas para obter uma taxa trivial de 100%. Um grupo vazio mostra Sem taxa/0–0, mesmo que o documento total seja AVAILABLE. A ausência do PBP não gera documento de zeros. INSUFFICIENT bloqueia taxa e gráfico, inclusive nas projeções, e conserva contagens confirmadas.

`project` devolve um objeto de apresentação. Nenhum DTO é alterado para simular outro documento. O aprofundamento reutiliza SituationalContent sobre o documento original completo, com aviso da diferença de população. Única extensão do componente compartilhado: prop opcional `announce` (default true) para evitar anúncio duplicado no explorador; a leitura anterior continua idêntica por padrão.

## Fixação, comparação e foco

Recortes fixados guardam identidade de documento/fonte, pergunta e refinamento; números, unidade, time/lado, jogos/semanas/adversários e versões vêm desse documento validado. A investigação ativa não os modifica. Há remoção e substituição explícitas; um recorte duplicado não ocupa outro lugar. Ao atingir dois, Fixar orienta a remover/substituir, sem descartar automaticamente o primeiro.

A comparação prioriza mesma família, pergunta e refinamento (portanto o mesmo significado de numerador e unidade). Valores são descritivos; não há diferença numérica, mesmo entre compatíveis. Famílias/refinamentos diferentes recebem aviso de leitura contextual. Jogo em comum recebe aviso de períodos sobrepostos e amostras não independentes. Ataque e defesa são atribuídos explicitamente. No mobile, cada identificação e seus números ficam em sequência vertical.

Mudar pergunta/lado/período/refinamento não move o foco para o título nem manda rolar ao topo. Há um anúncio polite/atomic curto do contexto e resultado; o documento completo no aprofundamento usa aria-live off. Mudanças em expansíveis usam comportamento nativo. Substituição conserva o botão; remover direciona foco ao título da comparação ou à ação Fixar quando some o último item. Não foi feita avaliação com leitor de tela humano.
