# Decisões do hub de modelos

Cada entrada: data, decisão, motivo, quem decidiu. Itens "aberto" esperam o dono do projeto.

| # | Data | Decisão | Motivo | Quem |
|---|---|---|---|---|
| H-D1 | 24/11/2026 | Hub de vários modelos como objetivo; fundação antes de modelos de produto | Pedido do dono: "hub de modelos", portfólio de ML engineer | Dono |
| H-D2 | 24/11/2026 | Publicar previsões no site é aceitável (com novo `schemaVersion`), mas fica para o próximo plano | Dono: "não tenho problema com publicar"; contrato público exige versão e ADR | Dono + orquestrador |
| H-D3 | 24/11/2026 | Aquisição própria do nflverse para `HUB/raw`, sem usar nem alterar o raw da ETL | Raw da ETL só tem 2023, 2025 e 2026 semanas 1–2 (facts/etl-data.md §2); ETL fora do escopo | Orquestrador |
| H-D4 | 24/11/2026 | Temporadas de 2011 até a corrente | Regra de kickoff estável desde 2011; volume suficiente para EP | Orquestrador |
| H-D5 | 24/11/2026 | Só scikit-learn/numpy; modelos persistidos como JSON + pyfunc em código; sem pickle | Mesma garantia do plano MLflow; evita dependência nativa (`libomp`) | Orquestrador |
| H-D6 | 24/11/2026 | Primeiro modelo: Expected Points (7 classes, próximo placar na metade) | Base para WP, 4º down e PROE | Dono aprovou a fundação proposta |
| H-D7 | 24/11/2026 | Mesmo home do MLflow, experimentos/modelos com prefixo `hub-` | Uma UI só; prefixo isola de experimentos importados | Orquestrador |
| H-D8 | aberto | Publicação do branch do MLflow (208 commits locais por baixo) | Repositório é público | Dono |
| H-D9 | 24/11/2026 | Siglas normalizadas para a franquia atual (OAK→LV, SD→LAC, STL→LA) em `plays`, `games` e `team_*`, com a sigla original preservada em coluna própria; o histórico (EWM) atravessa a mudança de cidade | Revisão C1: PBP usa siglas atuais e schedules as históricas, invertendo placar em 160 linhas; mesma franquia e elenco | Orquestrador |
| H-D10 | 24/11/2026 | Cache bruto endereçado por sha256 (arquivos nunca sobrescritos); manifesto só gravado depois de todos os arquivos validados | Revisão M2/M3: refresh invalidava aquisições antigas e falha no meio deixava manifesto inconsistente | Orquestrador |
| H-D11 | 24/11/2026 | Idempotência do backtest inclui impressão digital dos dados e do código dos modelos, calculada pelo harness; registro exige que o modelo final seja o selecionado no backtest com os mesmos hiperparâmetros | Revisão M4/M5 | Orquestrador |
| H-D12 | 25/11/2026 | Mercado (spread e moneyline de fechamento) entra como referência fora da regra, não como feature, em ratings e WP pré-jogo | Comparação "modelo × mercado" é o insight; usar o mercado como feature tornaria o modelo uma cópia dele. Linha de fechamento é conhecida antes do kickoff | Orquestrador |
| H-D13 | 25/11/2026 | Splits semanais (treina com tudo antes da semana, testa na semana) para modelos de jogo | É a cadência real de uso; tamanho dos dados (≈4 mil jogos) permite | Orquestrador |
| H-D14 | 25/11/2026 | Merge em `main` só com confirmação explícita: o Vercel publica `main` em produção | Integração Git do Vercel ativa (deploys de preview nos PRs) | Orquestrador |
