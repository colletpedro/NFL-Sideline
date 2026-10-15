# Aceite E5c-2 — projeção offline, 15/10/2026

Aceita no escopo de projeção/validação/CLI offline. Candidata
`3cfccdb656cbc5caf21dcfb82c1d8cb3a064a0c7`, sobre
`35e3afcb52bf3aa99fbfda40401920b8c393bf24`, incorporada sem correção de código
à branch local `codex/metrics-integration-e5c2`. Worktree candidata preservada.

## Revisão independente

Revisados núcleo, entrada nominal, requalificação de envelopes, rederivação da
materialização, publicação/leitura, fixtures, testes e script da prova real.
O reader confere hashes e reconstrói a cadeia aceita e a própria projeção;
não confia no observationId ou marcador externo para promover garantias.
O núcleo puro mantém pré-condição explícita de fonte verificada, enquanto as
entradas públicas de arquivo executam essa verificação a cada leitura.

Reproduzidos **397 testes Python** (42 novos e 355 regressões selecionadas),
**17 testes E5c-1**, schema e validação semântica E5c-1 dos **54 documentos**
(seis sintéticos e 48 reais), além de `git diff --check`. Não foram repetidos
SQL/Java/frontend porque seus componentes permaneceram idênticos.

A prova real foi repetida em diretório novo:
`/private/tmp/nfl-e5c2-orchestrator-real-20261015`, sobre a materialização E5b-6
aceita, sem banco, harness, aquisição, escrita nos originais ou novos receipts.
Produziu o mesmo bundle e os mesmos seis hashes de arquivos da candidata;
o extrato de observações versionado confere byte a byte com a saída própria.
Geração → cópia → remoção da saída inicial → leitura da cópia passou.

Resultado: **48 observações**, **72 verificações de grupos por membro**, sendo
**48 grupos distintos de cobertura/time/papel/fundamento**. Os períodos W1, W2
e W1–2 se sobrepõem; 72 não significa 72 amostras independentes. A lacuna
`2026_03_BAL_DAL` permanece ABSENT/null. NE/POST2025 é referência separada.

[Prova real própria](real-proof.json), [contraprovas](review-probes.json),
[schema/semântica](semantic-contract-validation.json) e
[hashes/preservação](verification.json) registram o escopo. A checagem de schema
usa Python/jsonschema existentes fora do venv ETL; o runtime não depende deles.
Nenhuma instalação foi feita. Os probes usam /private/tmp explícito, evitando
os aliases de diretórios temporários que o guard de symlink corretamente recusa.

## Contraprovas adicionais

Sobre bundle sintético operacional, alteramos separadamente EPA, completude e
garantia temporal. Recalculamos observationId, índice/mapa do manifesto, bundleId
e todos os hashes físicos externos. Nos três casos a leitura recusou a saída
por divergência da derivação dos originais. Isso prova esses vínculos mecânicos;
não autentica origem externa nem reimplementa a seleção PIT.

Reprodução na raiz, com dependências já existentes e destino de relatório NOVO:

```bash
export PYTHONPATH=etl-pipeline/src
export PYTHONDONTWRITEBYTECODE=1
NFL_E5C2_REVIEW_PY='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python'
"$NFL_E5C2_REVIEW_PY" -B docs/plans/metrics/e5c-2-review/probes.py \
  --real-observations docs/plans/metrics/e5c-2/real-observations.json \
  --output /private/tmp/nfl-e5c2-review-probes-new.json
```

Esse comando usa o extrato apenas para contar os grupos; a mutação/recusa usa
a fixture autocontida sintética, sem depender de /tmp histórico. A prova real
completa exige os originais locais aceitos: execute o comando de real_proof.py
do README E5c-2 com workspace novo. Se faltarem, ela fica pendente; nenhum
relatório resumido substitui a materialização.

## Limites aceitos

- Completude, expectativa demonstrada, modelo EPA e conhecimento temporal dos
  dados reais continuam UNKNOWN. EPA observado preservado não habilita comparação.
- unknownFilterFlagsN é contexto de jogo, não medida por time/fundamento. O
  manifesto e as limitações precisam acompanhar os documentos no futuro adaptador.
- Arquivo vazio sem observação vinculada ao jogo não sustenta volume zero. A
  contraprova e a proposta de evolução permanecem; contratos congelados intactos.
- O bundle completo é autocontido, mas volumoso (cerca de 57 MB). O extrato
  versionado não é bundle auditável. Não transportá-lo como prova de linhagem.
- Não há comparação, elegibilidade pregame, avaliação editorial ou compreensão
  humana comprovada. O reader não autentica autoridades das premissas de origem.

## Continuação e preservação

Próxima entrega: **E5c-3, adaptador explícito para o laboratório local**, partindo
somente de bundle validado e transportando documentos, fieldScopes, períodos,
denominadores, motivos e limites. Não enviar fontes brutas, receipts ou caminhos
históricos ao browser. Validar o transporte antes da evolução da apresentação;
não ampliar o contrato visual v1 ou conectar a API principal implicitamente.

Os 23 arquivos candidatos foram conferidos por hash e permanecem idênticos.
Adapter/writer/seleção temporal/SQL/Java/frontend/contratos/workflow/snapshots
aceitos e 36 arquivos históricos não rastreados foram preservados. A única
mudança adicional de estado fora do novo pacote de revisão é documental.
Sem .env, banco remoto, modelos, processo semanal, merge em main, push ou deploy.
