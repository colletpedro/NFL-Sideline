# Projeção privada broadcast-team-w12-v1

Projeção 1.0.0, política broadcast-team-policy-1.0.0, índice pinado próprio e 32 documentos em teams/TEAM.json. Cada índice lista código, jogos, adversários, caminho fixo e SHA-256 do documento; temporada/fase/semanas e coleção de origem explícitas. COMPLETED.json fixa todos os arquivos. request.json fixa o pedido; policy.md e source-receipt.json acompanham. source/matchups contém cópia física completa do pacote W12, inclusive fontes originais.

Documento: scope (time, 2026 REG [1,2], retrospectivo), dois games com identidades/calendário/hash, duas productions. Cada produção contém perspectiva/label/oponentes, components com produção semanal original e hash, metrics terceira/redZone (descritor, display/aggregate, observação agregada, originais e reconciliação), três epa com soma/denominador/contagens/IDs e observação agregada original, thirdAttempts/redZoneCampaigns reais e partição conjunta. comparisons concede/recusa por operação. facts tem evidência e permissão. definitions/policy/sources/guarantees/limitations preservam procedência e UNKNOWN.

Numerador/denominador do agregado indisponível são null, não um total parcial apresentado como W1–2. Componentes válidos continuam rastreáveis. NO_OPPORTUNITIES tem 0/0 e nenhuma taxa. Modelo/completude UNKNOWN não viram COMPLETE. Não há referência agregada da liga.

Reader valida identidade/árvore/hashes, reexecuta reader integral da coleção autocontida e reprojeta os documentos, confrontando os originais. Publicação e reprodução em destinos novos exclusivos, nunca overwrite. Recuperação física deve ser idêntica e reproduzível sem origens externas.

Nova fronteira GET /__team-w12/ (índice) e /__team-w12/TEAM (documento), com X-Local-Team-W12: 1 e X-Team-Collection: pin. Host/Origin exatos de 127.0.0.1:18105, corpo vazio, método GET; query/subpath/duplicatas recusados. Snapshot validado antes de servir, congelado; hash por documento e coleção. Sem paths de arquivo por URL, sem fallback. Fontes/configuração escolhidas pelo operador, artefato nunca em public/data. Fronteiras antigas na nova instância mantêm a mesma restrição, parametrizadas coerentemente para 18105.
