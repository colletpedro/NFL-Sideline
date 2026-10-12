# Fixtures E5b-4

Pequeno calendário REG congelado, sem leitura de games SQL; IDs synthetic-* já
preparados pelo harness aceito. Três jogadas: soma geral exata -1, EPA zero
observado, positivos/negativos com 39 casas que se cancelam. Partições A+B+A
preservam multiplicidade sem duplicar amostra. synthetic-5 fica sem fonte;
synthetic-6 só recebe COMPLETE vazio em um cálculo separado explicitamente
construído pelo harness. Alvo synthetic-3 é excluído por ID.

`build_fixture.py` usa fontes versionadas e adapter/archive aceitos; gera archive
**novo** e receipts da execução atual. Nunca copia um archive/receipt histórico.
Os documentos auxiliares gerados declaram fatos sintéticos com origem
synthetic-e5b4, recorded_at explícito e dependência do documento METADATA recebido;
não certificam dados reais. PIT antes dos receipts atuais permanece UNKNOWN.
Lote com dois jogos observados é contraprova, não materialização aceita.
