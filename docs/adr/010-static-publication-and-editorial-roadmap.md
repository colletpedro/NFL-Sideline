# ADR-010: publicação estática e roadmap editorial

Status: aceito; fundação estática publicada. Fast track editorial v0 implementado localmente e validado offline,
ainda não integrado a banco/Gemini reais nem publicado.

## Decisão atual

Java permanece como núcleo de domínio, API REST local e exportador batch. Production consome snapshots JSON versionados, sem servidor Spring permanentemente hospedado. O exportador publica apenas caches existentes e nunca chama Gemini.

Calendário é independente de mercado. Jogos sem odds são persistidos e publicáveis, com ausência de mercado explícita. Pares completos de moneylines e seus mercados são atualizados juntos; observações parciais/ausentes preservam a última cotação completa. PBP ausente não autoriza métricas fabricadas nem de outra temporada. A temporada padrão vem do manifest e a semana inicial é escolhida pelas datas dos jogos, mantendo seleção manual. Estas regras de disponibilidade não implementam profundidade editorial.

## Política editorial manual

- rodada operacional atual: análise pregame FULL;
- rodada cronológica seguinte: análise pregame BASIC, explicitamente preliminar;
- segunda rodada futura em diante: nenhuma análise pública;
- jogos encerrados preservam a seleção pregame publicada; postgame permanece fora do escopo;
- versões são inserts imutáveis e regeneração exige novo `revisionKey`;
- geração e publicação são ações manuais separadas por manifesto editorial versionado;
- o snapshot permanece no schema v1 e projeta ambos os tipos internos como `matchup`.

O fast track não altera o schema do banco. Os tipos internos são `matchup_full_v0` e `matchup_basic_v0`; registros
legados `matchup` são não classificados e não entram automaticamente na seleção nova.

O manifesto permanece vazio nesta implementação. O primeiro rollout editorial deverá preencher manualmente as
seis análises pregame legacy da Week 1 já publicadas, sem atualizar/clonar linhas: cada entrada usará o ID e os
hashes da linha imutável, `depth: "LEGACY_PUBLISHED"`, e só será aceita para jogo encerrado quando conteúdo e
`createdAt` coincidirem exatamente com o snapshot público anterior. Esse modo interno não altera o schema
público v1, que continua expondo `analysisType: "matchup"`.

Para FULL/BASIC, publicação reconstitui a janela tanto em `asOfDate` da geração quanto no `--as-of` explícito
do snapshot. Revisão posterior ao gameday é rejeitada. O corte de métricas da postseason permanece limitado pelo
schema sem fase/data: o resolver é cronológico, mas o contexto degrada explicitamente e não reivindica suporte
completo.
