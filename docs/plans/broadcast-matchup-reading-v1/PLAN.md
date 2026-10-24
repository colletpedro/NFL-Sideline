# Página piloto de leitura · NYJ × TEN W1

Plano anterior à implementação. Base conferida limpa: `3c1a99b675cb4182323952ab08be8a7d8658175a`, branch `codex/broadcast-comparison-foundation-v1`. Worktree gerenciada nova `broadcast-matchup-reading-v1`, branch `codex/broadcast-matchup-reading-v1`. 18102 livre; listeners anteriores 18098/18099/18100/18101 preservados.

Observação prévia real em 18100: explorador apresenta time/lado/período/pergunta antes de 2/10, com distância em controle próprio; captura `evidence/before-explorer.png`. A nova página reúne os dois ataques e todas as famílias numa leitura vertical. Não se presume ganho de compreensão sem o estudo 3/5.

## Estrutura e direção

Entrada explícita `/?view=matchup-reading` no bootstrap experimental journey, com carregamento separado da página e CSS próprio. Home/App/explorador ficam intactos. Retorno por link normal para o explorador força a entrada anterior; nenhuma URL altera fonte/transporte. Piloto fixo por domínio, sem seletores de time/lado/período/família. Apenas Geral/Passe/Corrida no EPA, estado local.

Superfície em modo Read, preservando o mundo existente: ardósia #18232B/#24323C; painel contínuo #D6E1E6/#C7D3DC; tinta #15232C, apoio #3E5665, foco #17466A no painel e #D7F56B no cenário. Cores NYJ/TEN e logos transparentes existentes; Archivo para texto, Roboto Condensed para números. Sem novos ativos, cards repetidos, abertura gigante ou animação. Alinhamento à esquerda, números tabulares, seção com divisória discreta. O jogo é a unidade; os gráficos contam suas unidades reais.

Ordem: faixa compacta com resultado → três fatos com âncoras → EPA dos dois ataques → terceiras agrupadas por distância → red zone em ordem da fonte → mercado arquivado separado → método/procedência recolhidos. No mobile, cada distância mantém NYJ/TEN próximos; campanha é unidade visível. As referências compactas têm eixo 0–100%, empilhamento vertical para valores coincidentes sem deslocamento horizontal, pontos consultáveis por teclado/toque e alternativa textual.

## Mapa bloco → fonte → permissão

| Bloco | Fonte real | Permissão/limite |
| --- | --- | --- |
| Identidade/placar/data | StaticNflDataClient já usado por journey, listGames(2026), join exato gameId/REG/W1/NYJ/TEN | Sem placar constante ou substituto; erro de calendário impede resultado inventado |
| Resumo | facts.text/evidence/scope | facts.permission e vínculo às métricas/unidades; âncoras para terceira/red zone |
| EPA | productions.epa originalObservation.values.epa/descriptor/display | display + comparisons[foundation].sideBySide; formatRatio exato, escala comum somente geométrica; difference não usada; modelo UNKNOWN |
| Terceiras | metrics.third/thirdLong, thirdAttempts, thirdDistanceByType | display + comparisons.third.sideBySide; uma marca por ID; faixas/tipos vêm da unidade real |
| Red zone | metrics.redZone e redZoneCampaigns | display + comparisons.redZone.sideBySide; uma campanha por marca, 100% sempre junto de 1/1 |
| Liga | leagueReferences.third/redZone.teamRateDistribution/inventory/pooledRate | permission leagueReference; mesma escala, sem ranking/percentil, piloto incluído e não independente |
| Mercado | market.records/sources/reasonCodes | Campos brutos, sem interpretar spread ou afirmar captura pré-jogo/fechamento |
| Método | definitions.document, policy, guarantees, sources e unidades | Regras curtas próximas; exclusões/penalidades/versões/hashes/UNKNOWN recolhidos |

## Integração e verificações

Config própria de operador fixa caminho físico/pin. Nova fronteira somente na configuração experimental do piloto, usando reader Python existente sem mudar processamento: validação no startup, bytes congelados, GET mesma origem com Host/Origin/marcador/método/corpo/rota controlados. 18101 não é relaxado nem chamado diretamente pelo browser. Fonte falha produz indisponibilidade honesta, sem fixtures/fallback.

Testes reais: seis EPA/denominadores, 22 tentativas, quatro campanhas, distribuição conjunta, 32/31 pontos/ATL, fatos/permissões e calendário/placar. Sintéticos somente em testes para estados, recusas e incompatibilidades. Frontend completo, lint, builds experimentais/público, cinco falhas esperadas preservadas e hashes públicos iguais. Navegador 1440/390/320, fonte 200%, teclado/foco, âncoras, EPA, detalhes, recarga/link direto e fonte indisponível. Capturar, inspecionar, corrigir em lote e restaurar viewport/fonte. Documentar provas, roteiro 3/5, commits, HEAD/árvore e PID/encerramento. Sem estudo com pessoas, merge/push/deploy/publicação/promoção.

## Orientações consultadas

Impeccable não instalada nas raízes locais. Consultadas somente as orientações oficiais [SKILL.md](https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/SKILL.md), [new-work](https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/reference/new-work.md), [operate/Read](https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/reference/operate.md) e [craft floor](https://github.com/pbakaus/impeccable/blob/main/.agents/skills/impeccable/reference/craft-floor.md). Sem launcher, instalador ou scripts remotos. Aplicação: leitura precisa, hierarquia contínua, foco/contraste e verificação renderizada. Identidade aprovada prevalece. Skills locais frontend-design e ui-ux-pro-max apoiam composição e acessibilidade; consulta focal de foco e React, sem gerar outra identidade visual.
