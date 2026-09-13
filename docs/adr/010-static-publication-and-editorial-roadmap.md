# ADR-010: publicação estática e roadmap editorial

Status: aceito para a fundação estática; política editorial registrada, ainda não implementada.

## Decisão atual

Java permanece como núcleo de domínio, API REST local e exportador batch. Production consome snapshots JSON versionados, sem servidor Spring permanentemente hospedado. O exportador publica apenas caches existentes e nunca chama Gemini.

Calendário é independente de mercado. Jogos sem odds são persistidos e publicáveis, com ausência de mercado explícita. Pares completos de moneylines e seus mercados são atualizados juntos; observações parciais/ausentes preservam a última cotação completa. PBP ausente não autoriza métricas fabricadas nem de outra temporada. A temporada padrão vem do manifest e a semana inicial é escolhida pelas datas dos jogos, mantendo seleção manual. Estas regras de disponibilidade não implementam profundidade editorial.

## Direção editorial futura

- semana atual: análise pregame completa;
- próxima semana: pregame forte/preliminar;
- semanas posteriores: preview básico;
- jogo encerrado: postgame passa a ser a visão principal;
- previsão pregame original permanece imutável e acessível para comparação;
- análises são versionadas e nunca sobrescritas silenciosamente;
- mudança de semana promove a profundidade do próximo conjunto;
- métricas situacionais futuras permanecem em standby.

Este ADR não define prompts finais, novo schema de banco nem taxonomia definitiva. Essas decisões exigem pacotes posteriores e migrations próprias quando aplicável.
