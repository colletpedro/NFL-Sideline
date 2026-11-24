# Aceite E5b-6 — dados locais reais, 13/10/2026

**Aceita no escopo limitado e incorporada localmente.** Candidata
`c5bfa75993f50384f1e6221516f83576d7d0bcde`, base
`f8a258b64116aa7f67f4d4d6253d3f00dc91f5e2`, branch
`codex/metrics-integration-e5b6`. Componentes anteriormente aceitos permaneceram
byte a byte iguais; não foi necessário corrigir a implementação nesta revisão.
Main continua em `5096a585f0cc5455160ff9c2ee64555cfcb59fc0`.

## Verificação independente

O orquestrador leu protocolo, congelamento, auditor racional, harness, reconciliação
SQL/legado, gate e testes. Reproduziu:

- **498 testes ETL e nove testes do auditor**, sem falhas/skips;
- 26 exemplos/23 testes E5a, 12 hashes, regressões E5b-1/2/3/4/5;
- inventário e cópias novas dos quatro Parquets reais, **14.995.734 bytes**;
- planejamento, duas execuções completas do ETL local em PostgreSQL 17.6 próprio;
- reconciliação de todos os jogos/grupos com acumulação racional independente;
- extração/materialização, três pedidos PIT e três leituras Java reais, usando
  JAR reconstruído offline com testes Java desativados, pois o código não mudou;
- diff contra a base, 56 hashes de fontes/testes/harness/gate e preservação de
  36 arquivos históricos não rastreados.

As 51 regressões SQL constam da candidata e já tinham sido reproduzidas pelo
orquestrador na E5b-5. Não foram repetidas nesta revisão: schema/writer/runtime
aceitos não mudaram. A carga de **dados reais** desta entrega foi repetida em
instância nova, independentemente da carga da candidata.

[Gate offline](offline-verification.json), [prova real selecionada](real-proof-summary.json),
[reconciliação da integração](integration-verification.json). O gate foi executado
no checkout exato candidato; suas restrições documentais de base não são promessa
de execução sem adaptação em branches posteriores que atualizaram o estado/aceite.

## Resultados reconciliados

| Escopo | Observados/calendário | Elegíveis |
|---|---:|---:|
| 2025 REG | 272/272 | 32.813 |
| 2025 POST | 13/13 | 1.689 |
| 2026 REG, bytes PBP W1–2 | 32/272 | 3.830 |

Persistidos dois lotes, **557 coberturas/associações e 3.804 grupos**. Os 240 jogos
sem observação em 2026 permaneceram sem grupos zero. A reexecução inseriu zero
e reutilizou **4.978 registros**, mantendo IDs, linhas, persisted_at, blobs,
receipts e journals anteriores. Novas tentativas/runs permaneceram separados.

O auditor lê os bytes com Polars e soma `Fraction(Decimal(str(value)))`, sem usar
os acumuladores do adapter. Reconciliou população, exclusões, fontes, dedup,
denominadores, somas, ataque/defesa, passe/corrida e identidade das associações.
Médias legadas foram auditadas separadamente com tolerância float explícita;
essa tolerância não sustenta a igualdade das somas novas.

O inventário da revisão conferiu os mesmos quatro hashes registrados pela
candidata e pelas auditorias anteriores. Originais, inclusive os arquivos 2023
inventariados e excluídos, foram rehashados e preservados. Não houve aquisição.
2026 descreve um conjunto arquivado W1–2, **não atualização da semana atual**.

## Garantias e limites de uso

Materialization-v2 → input-v3 → algoritmo 1.1.0 → result-v3 passou. Os três pedidos
PIT permaneceram sem agregados e com expectativa UNKNOWN; trustedOrigins vazio
e nenhuma evidência auxiliar histórica ou de encerramento foi acrescentada.
Leitura Java desses resultados verifica contrato/integridade; não prova, por
esses pedidos vazios, uma comparação editorial de números reais.

Observação de todos os jogos 2025 não certifica completude. Modelo EPA,
disponibilidade/ingestão histórica e encerramento continuam UNKNOWN.
Receipts atuais e hashes provam apenas as garantias locais documentadas.
O aceite comprova a cadeia e reconciliação dos bytes selecionados, não autentica
o fornecedor nem libera comparação certificada, geração editorial ou publicação.

Não foi encontrada revisão real alternativa nessa raiz; correções/falhas
sintéticas de regressão não foram apresentadas como revisão autêntica upstream.

## Instância e evidência local

Revisão: UUID `d5b4ba1a-4c11-44a0-83ef-532771992c0f`, banco
`nfl_e5b2_d5b4ba1a4c11`, porta 49667, root
`/private/tmp/nfl-e5b6-instance-orchestrator-20261013`. Encerrado pelo próprio
harness: pg_ctl=3, PID/listener ausentes e probe de bind aprovado.
Nenhum cluster histórico ou serviço global foi administrado.

Workspace `/private/tmp/nfl-e5b6-orchestrator-real-20261013`: Parquets congelados,
archives, journals, snapshot/extração, input/lineage, resultados e relatório
integral permanecem locais. A prova selecionada registra o caminho/hash do
relatório integral; esse hash não recupera arquivos locais ausentes. Testes
offline são reproduzíveis sem esses dados; repetir a carga real exige os bytes
autorizados e runtimes existentes. Credenciais e arquivos volumosos não foram
versionados.

## Continuação do plano

**E5b-6 concluída no escopo de backfill/auditoria local.** A próxima preparação
deve fechar a política de proveniência/completude e o contrato de consumo das
métricas: observação auditável, comparação certificada e conhecimento no corte
são garantias distintas. Projetar coleta prospectiva/estados de jogo sem retrodatação,
e definir explicitamente como subsets/UNKNOWN chegarão aos consumidores.
Atualizar os bytes de 2026 exige uma entrega própria de aquisição autorizada.

O plano pode preparar consumidores descritivos que conservem os limites, mas
não deve anunciar comparação certificada disponível com estes dados.
Supabase completo/advisors antes de aplicação fora do cluster descartável,
rodada humana E4, BASIC/FULL, defeitos legados e rollout público continuam pendentes.

Nesta revisão não houve carga/migration remota, aquisição, .env, modelos,
alteração de componente aceito/Java/frontend/workflow/snapshot/aprovação,
integração editorial, merge em main, push ou deploy.
