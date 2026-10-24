# Plano nominal anterior à geração · entrega 5/5

Pedido: “NFL Sideline — Entrega 5/5, Hub semanal, página do time e continuidade da exploração”. Base exata conferida limpa `945368956571cfc63ec1604337245fe822a138bc`, branch `codex/broadcast-matchup-w12-v1`. Nova worktree gerenciada `broadcast-hub-team-w12-v1`, branch `codex/broadcast-hub-team-w12-v1`. Referência 18104 e anteriores preservadas. Sem rede de dados, credenciais, banco, Gemini, ativos novos ou dependências novas.

## Percurso e URLs

Hub `/?season=2026&week=1` ou `week=2` → confronto `/?view=matchup-w12&game=ID` → participante `/?view=team-w12&team=BAL&season=2026` → seus dois jogos → retorno à semana. Contexto usa `returnWeek` e preserva `q/scope/filter/page`; nunca altera o recorte dos dados. Confrontos continuam semana única; times fixos W1–2. IDs/períodos/duplicatas incompatíveis recebem erro, sem substituto. Piloto/explorador/legacy/W12 anterior permanecem entradas secundárias. Nova entrada e config própria 18105, loopback/strictPort; não modificar configuração 18104.

## Hub

Identidade compacta do arquivo 2026 → semanas horizontais W1/W2 com 16 jogos cada, imediatamente visíveis → busca existente estendida para distinguir sugestões de time e partida desde a primeira letra → destaque horizontal → dois apoios → 13 itens compactos → diretório dos 32 times. Todos os jogos em DOM, sem busca obrigatória/carrossel. Destaque e apoios: primeiros três em ordem cronológica de gameday, desempate por gameId; critério de apresentação, sem importância esportiva inferida. Links “Ver confronto” e “Ver time” separados, sem links aninhados. Busca reutiliza normalização e mecanismos de teclado/foco/Escape de GameSearch, com destinos explícitos. Não adicionar seletores analíticos ao hub.

## Time

Identidade com logo transparente → 2026 REG W1–2, dois jogos observados → síntese de razões e contagens sustentadas → EPA, “TIME com a bola” e “Adversários contra TIME” juntos, fundamento local → terceiras e red zone com as duas perspectivas → jogos componentes (semana/adversário/placar/link) → método recolhido. Segunda perspectiva agrega produção real dos adversários, não outra confirmação. Sem nova liga agregada, ranking, tendência, nota ou prognóstico. Reusar formatação exata, escala, marcas/legendas onde adequado; não aplicar elegibilidade situacional ao EPA. Mensagens concretas de ausência/zero preservam estados/permissões.

## Dados e fronteira

Nova projeção privada `broadcast-team-w12-v1`, versão 1.0.0, índice de 32 documentos/pin próprio. Entrada imutável: coleção W12 operacional `sha256:f949be3e095b1348fb10feabc7b202ee0fabc46ab737945070755e0f02c757bc`. Copiar fisicamente a coleção inteira para o novo pacote durável, verificar fontes e manter recuperação/reprodução em destinos novos. Nenhuma dependência de outra worktree/processo. Reader completo antes de servir; snapshot congelado e fronteira própria com Host/Origin/método/marcador/pin/caminho estritos. Configuração somente pelo operador.

Agregação por união de unidades, soma de numeradores e denominadores; EPA soma decimal exata / n finito. Preservar faltantes/não finitos, definições, jogos, adversários, observações originais W1–2 e unidades. Reconciliar ambas as perspectivas dos 32 times com os originais EPA/situacional completos dentro das fontes. NO_OPPORTUNITIES pode contribuir zero; fonte ausente/insuficiente bloqueia o agregado pretendido, sem omitir semana, mantendo componentes válidos. Completude/modelo/historicidade UNKNOWN. Auditor independente sem chamar projetor como oráculo.

## Identidade visual e verificação

Identidade aprovada prevalece: ardósia #18232B/#24323C, painel #D6E1E6/#C7D3DC, tinta #15232C, apoio #3E5665; cores dos times, Archivo e Roboto Condensed. Hierarquia destaque/painel/item compacto; alinhamento à esquerda e divisórias discretas. Logos existentes, variantes brancas por contraste, sem placas claras. Sem capacetes quando não houver par apropriado, retratos ou animação de entrada. Skill frontend-design aplicada à hierarquia, não à reinvenção da identidade.

Inspeção prévia real: hub 18104 possui busca primeiro, W1/W2 e grade homogênea; sugestões atuais só abrem jogos. Captura preservada. Conferir todos os 32 times/64 perspectivas e unidades, somas/estados/arredondamentos, agregados originais, HTTP/recusas/hashes/cópias e reprodução independente. Testes sintéticos somente em testes para ausência/insuficiência/zero+válido. Navegação com retorno, busca de time e jogo, histórico, resposta tardia, erro/falha independente; visual 1440/390/320/200%, teclado e todos os logos. Python/frontend/lint/TypeScript/builds/isolation e cinco falhas esperadas preservados. Sem novo estudo humano: P01/N=1 e EPA sem reconfirmação continuam limites.
