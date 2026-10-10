# Fixtures sintéticas temporais independentes

Nenhum instante/receipt representa os Parquets locais históricos ou autenticação
externa. A origem `synthetic-system` é premissa deliberada destes testes. Bytes
FILE são pequenas strings sintéticas versionadas em base64; não dependem de archive,
cluster ou dados de /tmp. Os campos temporais são materializações artificiais.

`ledger.json` foi escrito manualmente, sem executar select/aggregate. `alpha` tem
2 passes com soma1/E2/S1. `beta` tem passe N4/E3/S1/soma-1 (um EPA ausente) e
corrida N2/E2/S1/soma0.5. Geral completo: N8/E7/S3/soma0.5, EPA1/14, SR3/7;
frequência passe6/8=3/4 e corrida2/8=1/4. Não é média dos jogos/fundamentos.
`gap` é FINAL elegível, sem PBP: expectativa3, fonte completa2, cobertura2/3.
W2 é bye sob calendário completo/período fechado; W3 tem dois eventos distintos.
Target foi deliberadamente rotulado W1/FINAL/bound anterior, mas pedido é W4:
continua excluído por identidade. Kickoff documentado é posterior ao corte.

Correção de alpha tem soma4/E2/S2 e bytes/declaração recebidos em outubro.
PIT em setembro a rejeita; reconstruction a escolhe nominalmente e soma3.5/E7
=> EPA1/2. `beta-composed` possui uma partição anterior e outra de outubro:
PIT rejeita a revisão inteira, sem recuperar partes convenientes.

`package-unproven.json` conserva hashes e envelopes, mas origins não são aceitas,
receipts são prospectivos de outubro e ingestão não está comprovada. PIT não
seleciona calendário nem métricas; expectativa é null, pregame não é certificado.
Não é um atalho para certificar os dados históricos reais.

Os testes parametrizados acrescentam contrafactuais independentes: instante
igual ao corte, frações de nanossegundo, DST, correção de calendário/estado,
metadados/evidências tardios, aliases e conflitos, modelos por arquivo, histórico
POST separado, flags/EPA desconhecidos, fonte completa vazia e falha de publicação.
Oito ledgers temporais E5a são materializados sob origem sintética explícita;
labels de receipt do E5a não são convertidos em receipts reais históricos.
Somente as somas dessa tradução usam o adapter E5b-1 aceito; expectativas de
jogos, cobertura/bye/janelas e frações são os ledgers E5a independentes.
