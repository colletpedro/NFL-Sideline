# NFL Sideline · Referência visual experimental v1

Referência local adotada nesta entrega, em 21/10/2026. Implementação **v4**, commit `840e3603920b3db15dca44116d2072f5a8528d4f`, branch `codex/broadcast-axis-baseline-v4`. Base: v3 `9c43b06c91c146357009f28774c693ddfd78a306`. Este pacote documenta o que já está implementado; não extrai uma biblioteca nem integra o consumidor real.

[Telas e reprodução](SCREENS.md) · [Limites e próxima fronteira](LIMITS-AND-NEXT.md) · [Relatório da correção](../../plans/broadcast-axis-baseline-v4/REPORT.md).

O briefing do usuário registra aprovação favorável da direção: cenário ardósia, cores fortes dos times, painéis contínuos, Archivo/Roboto Condensed, gráficos integrados e estados próprios. Também informa revisão do acabamento v3 pelo orquestrador e preservação das decisões/números em 54 recortes e oito casos de borda. Esses são os antecedentes desta referência. Não houve nova aprovação humana da v4 nem pesquisa com participantes nesta entrega.

## Identidade implementada

Fonte dos valores: [experience.css](../../../web-ui/broadcast-experience/experience.css), [fixtures.ts](../../../web-ui/broadcast-experience/fixtures.ts) e [ui.tsx](../../../web-ui/broadcast-experience/ui.tsx). As regras abaixo descrevem os papéis existentes, sem criar novos tokens.

| Papel | Material e comportamento |
| --- | --- |
| Cenário | `#18232B`, `#24323C`, luz radial discreta `#344752`. Fica atrás do conteúdo. |
| Cabeçalho e contexto | Navegação `#2C3D48 → #23323C`; faixa do confronto `#2B414E → #3E5360`; apoio editorial `#2D414E → #243640`. |
| Leitura contínua | Central e mesa compartilham painel `#D6E1E6 → #C7D3DC`. Tinta `#15232C`; apoio final `--muted: #3E5665`. Sem uma sombra/gradiente independente para cada métrica. |
| Identidade dos times | Duas regiões cromáticas contínuas, logos locais proporcionais, escala óptica por marca, cidade com peso menor, nome com presença. DAL `#2463A0 → #0B3057`; NE `#C90827 → #870016`. As demais cores e ajustes ópticos estão em `teams`. Cores identificam participantes, sem significar bom/ruim ou vencedor. |
| Contraste e divisórias | Tinta escura no painel claro; texto claro no cenário. Separadores de 1 px com branco/ardósia semitransparente. Cinza de complemento do sucesso `#B1C2CC`; linhas `#55717F`. |
| Ação | Ação principal em tinta escura, texto claro e altura mínima de 48 px. Links e botões explícitos, sem clique invisível no cartaz. |
| Seleção e foco | `#D7F56B` em sublinhados de navegação/seleção; fundamento ativo com fundo escuro. Foco de 3 px: amarelo no cenário, `#17466A` no painel claro. Controles têm estados semânticos como `aria-pressed` e `aria-expanded`. |

**Tipografia:** Archivo local para assinatura, manchetes, nomes, contexto, interface e explicações; Roboto Condensed local para placar e valores curtos. Manchetes e nomes usam aproximadamente 700–800; cidade e corpo preservam pesos menores e caixa normal. A leitura do recorte usa Archivo 700, 1,875 rem no desktop e 1,625/1,5 rem no mobile. Corpo em torno de 0,9375–1 rem, com entrelinha confortável. Dígitos tabulares, `font-synthesis: none`, largura natural e nenhuma compressão por `scaleX`.

As fontes continuam em `web-ui/local-editorial/matchup/assets/`, com licenças locais. Logos DAL/NE/BAL vêm do piloto; os demais têm [procedência registrada](../../plans/broadcast-experience-refinement-v2/ASSETS.md). O componente `Logo` mantém fallback por sigla. Não houve nova aquisição de ativos.

**Composição:** a abertura reúne identidade/placar, manchete e acesso principal, com análise de apoio lateral no desktop. A mesa integra identidade, resumo da partida, controles, gráficos, fato do recorte e volume no mesmo painel. A lista compacta usa linhas compartilhadas e status explícito; cada jogo não repete uma placa gigante. No mobile, a leitura segue essa hierarquia em uma coluna e a ação principal precede explicação e números da abertura.

## Componentes de referência

Todos os caminhos abaixo são relativos a `web-ui/broadcast-experience/`; os componentes continuam locais à entrada experimental.

| Região | Implementação | Regra observável |
| --- | --- | --- |
| Cabeçalho e navegação | `App.tsx`: `Header`, `PageFocus`; `state.ts`: `navigationContext`, `matchupHref` | Duelo atual, rodada do duelo e origem de retorno separados. URL preserva recorte e detalhes. |
| Identidade | `ui.tsx`: `MatchupBand`, `Logo` | Logos, nomes completos, cores e placar guardado por status. Pré-jogo usa VS. |
| Abertura e lista | `App.tsx`: `Home`, `RoundGames`, `Archive`; `ui.tsx`: `GameLink`, `ExploreLink`, `YardagePreview` | Rodada 7 com quatro jogos; hierarquia entre destaque e linhas compactas. |
| Filtros | `App.tsx`: `AnalysisControls` | Período e fundamento sincronizados com URL e leitura. |
| Gráficos | `Charts.tsx`: `EfficiencyChart`, `SuccessChart`, `ScoreTimeline`; `chartScale.ts` | EPA assinado; sucesso com contagem/denominador; placar identifica todos os quartos. |
| Síntese | `editorial.ts`: `readSlice`; `AnalysisReading.tsx`: `SliceReading` | Título nomeia métrica/fundamento. Contexto, amostra e apoios vêm do mesmo recorte. Atualização anunciada com `aria-live`. |
| Tabelas e detalhes | `AnalysisReading.tsx`: `StatSummary`, `AnalysisDetails` | Volume complementa os gráficos; detalhes oferecem tabela equivalente, situações e definições. |
| Pré-jogo | `App.tsx`: ramo de `Matchup`, `.matchup-summary`, `.pregame-agenda` | Um aviso de ausência; participantes, kickoff demonstrativo, local e outros destinos. Sem métricas/resultados da partida. |
| Ausência e recuperação | `Charts.tsx`: `.metric-absent`, `.missing-series`; `editorial.ts`: `recoverySlices`; `SliceReading` | “Sem fonte” difere de zero. Outros valores continuam visíveis; ações explícitas levam a recortes completos. |

## Regra adotada para o eixo de EPA

Domínio e posições continuam em `epaScale`: intervalo inicial −0,20…+0,40, ampliado em passos de 0,20 quando necessário; a escala é comum às séries do recorte. A v4 rotula **mínimo, zero e máximo**, mantendo as linhas intermediárias. `epaAxisLabels` seleciona rótulos e não muda domínio, coordenadas, comprimento das barras, sinais, unidades ou valores junto às séries. A fonte permanece em 0,6875 rem no eixo. A tabela equivalente continua disponível nos detalhes.

Esta apresentação foi verificada nos domínios utilizados pela demonstração, inclusive −0,20…+0,60, −0,40…+0,40 e série ausente. Não é uma certificação de legibilidade para domínios arbitrários ou de acessibilidade de todo o produto.
