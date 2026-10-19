# E5c-3R — reconstrução real candidata ao aceite

Os dados reais estão novamente disponíveis para o laboratório E5c-3 por uma cadeia
PostgreSQL → archive → extração → materialização-v2/input-v3 → reader/projetor
E5c-2 → DTO → sessão congelada → HTTP → apresentação. Não houve mudança dos
componentes aceitos, redesign, aquisição, publicação ou alegação de conhecimento
histórico. O aceite desta candidata permanece com o revisor.

## Base, isolamento e preservação

Base exata conferida: `ce06a6291d1a2e935871fef04f543a54489755f5`.
Branch: `codex/metrics-real-recovery-e5c3r`.
Worktree: `/Users/pedrocollet/.codex/worktrees/metrics-real-recovery-e5c3r/NFL Sideline`.
Estado inicial limpo. Checkout original permaneceu na branch
`codex/metrics-integration-e5c3`, mesmo HEAD, com seus arquivos históricos intactos.
Main permanece `5096a585f0cc5455160ff9c2ee64555cfcb59fc0`.

Commits locais de execução: `1723aa3` (protocolo antes da carga), `8c715d8`
(wrapper), `7ea6998` (formato UTC do pedido), `7b8f8f0` (restauração/provas reais) e
`512426e` (preflight das CLIs raiz para futuras reproduções).
O commit documental seguinte reúne relatório/inventários/evidências; HEAD final
é informado na entrega e pode ser conferido com `git rev-parse HEAD`.
As ocorrências intermediárias e sua resolução estão em [attempts.json](attempts.json).
Nenhum relatório histórico foi editado para aceitar uma nova execução.

[original-before.json](original-before.json) registra o estado inicial e hashes
históricos; [preservation.json](preservation.json) registra a conferência final.
Os 156 arquivos aceitos inventariados permaneceram com os mesmos SHA-256 da base;
as cinco CLIs raiz também conferiram (161 no preflight de futuras reproduções).
Diff de implementação restrito aos wrappers novos/documentação/ignore operacional.
Contratos, adapter, writer, seleção temporal, materializador, projetor, consumidor,
SQL, Java, frontend público, snapshots, aprovações e workflow foram preservados.

## Fontes e runtime reais

Somente os quatro arquivos nominais do checkout original, 14.995.734 bytes.
Todos os quatro SHA-256 informados na solicitação conferiram novamente antes da
carga e ao final. Cópias byte a byte congeladas; originais nunca modificados.
[inventário de fontes](inventory/sources.json) inclui paths, hashes completos,
schema inteiro, linhas, participantes, fases, semanas e jogos. Nenhum arquivo
2023 foi selecionado, lido para produzir números ou adquirido.

O runtime nativo antigo em `/private/tmp/nfl-e5b2-pg-runtime` desapareceu. Docker
já estava ativo e a imagem local PostgreSQL 17.6 foi identificada pelo ID imutável
`sha256:6942962433a569e87f228b4d4ab7e11db5deca64e43babb3a038443ad6c4f1bb`.
Usou-se `--pull never`, initdb vazio, entrypoint próprio, volume/UUID/marker novos,
porta host 50101 exclusivamente em 127.0.0.1 e servidor PostgreSQL em loopback
interno. Relay BusyBox nc já existente na imagem preservou o endpoint literal
exigido pelo guard; o guard verificou efetivamente `127.0.0.1:50101`, sem alteração.

Cluster final: UUID `b321d664-b54c-4d59-b56d-db30a726c1f1`, banco
`nfl_e5b2_b321d664b54c`. Apenas as três migrations versionadas necessárias foram
aplicadas à instância própria. Logins de domínio e writer separados, não
administrativos; roles, grants, RLS e marker dos harnesses aceitos preservados.
Não se usou o entrypoint Supabase nem qualquer banco/container histórico.
O inventário anterior à carga, espaço, imagem e código estão no preflight local.
Não houve instalação, download, `.env`, banco remoto ou serviço global iniciado.

## Reconciliação e derivação

| Bytes arquivados | Jogos observados | Elegíveis |
|---|---:|---:|
| 2025 REG | 272 | 32.813 |
| 2025 POST | 13 | 1.689 |
| 2026 REG, W1–2 | 32 | 3.830 |

O auditor E5b-6 independente releu os Parquets e acumulou Fraction/Decimal;
conferiu todos os game-audits, filtros, participantes, fases/rounds, contagens,
denominadores e somas exatas com artifacts e SQL. São 557 coberturas/associações
e 3.804 grupos. Os 240 jogos 2026 sem observação não receberam grupos zero.
O legado foi auditado separadamente; tolerância de médias float não fundamenta
a reconciliação exata das somas novas.

Primeira carga privada: 4.976 inserções; reexecução: zero inserções e 4.978
reutilizações. Todas as linhas privadas, persisted_at, blobs, receipts e journals
anteriores ficaram idênticos. A extração nominal completa foi capturada antes do
encerramento em transação read-only. Snapshot das onze tabelas e suas relações
estão preservados nas duas cópias, sem necessidade do banco desligado.

Receipts novos: 15, observados entre `2026-10-19T02:41:44.250637Z` e
`2026-10-19T02:41:46.562885Z`. Persistência SQL nova entre
`2026-10-19T02:41:44.324570+00:00` e `2026-10-19T02:41:46.918344+00:00`.
Materialização derivada em `2026-10-19T02:42:01.759837+00:00`; projeção em
`2026-10-19T02:42:06Z`. Esses são tempos reais da reconstrução (18/10 à noite em
Fortaleza), não disponibilidade/ingestão no passado. O wrapper não fabricou
receipts antigos nem promoveu timestamps SQL a conhecimento histórico.

O pedido nominal repetiu a coorte E5c-2 com associações da nova execução:
BAL/DAL 2026 W1, W2 e W1–2; ataque/defesa × general/passe/corrida; NE POST2025
separado; BAL W3 ausente. Reader público E5c-2 leu o bundle completo e rederivou
48 observações, com 72 reconciliações por membro (48 grupos distintos, períodos
sobrepostos). Valores/denominadores e garantias coincidem com o extrato histórico
apenas porque os quatro hashes de fonte são iguais. O extrato não foi fonte de
números nem substituto da linhagem. Não se usaram agregados de PIT vazio.

## Identidades históricas versus reconstruídas

IDs completos e nove associações nominais: [identities.json](inventory/identities.json).

| Identidade | Histórica | Nova | Motivo |
|---|---|---|---|
| Fontes, conjuntos, cálculo 2025/2026 e artifacts | hashes históricos | iguais | mesmos bytes/definições e projeção canônica sem path/relógio |
| Cobertura e associação temporal dos recortes | IDs históricos | iguais | mesma associação conteúdo/cálculo/cobertura/auxiliares; receipts não entram nessa projeção |
| Archive | `e12f94ce-9d5d-4646-92af-6ab06a4d9666` | `de4a91c9-3c53-444d-8656-0b8789cdad4e` | observação local/UUID novo |
| Receipts/execuções/SQL | apenas referências históricas disponíveis | novos | archive, root e instantes atuais; IDs individuais antigos não foram recuperados |
| Input temporal | `77e98040…` | `9dc7e6de…` | recursos FILE/receipts atuais |
| Materialização | `8b6c93fc…` | `f7a70f61…` | nova cadeia integral, SQL e derivação |
| Bundle | `8016e8dd…` | `2fae3be2…` | nova seleção de origem/derivação; pin novo |

Igualdade numérica e de algumas identidades de conteúdo não implica que esta
materialização seja a histórica. Nenhum ID foi renomeado para aparentar isso.

## Duas cópias duráveis e restauração

Run-id: `20261019T024130Z-50e03b27`.

- Principal: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/real-recovery/20261019T024130Z-50e03b27/`.
- Segunda cópia: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/backups/20261019T024130Z-50e03b27/`.
- Operações privadas/cluster desligado: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/operations/20261019T024130Z-50e03b27/`.

Cada cópia tem 162 arquivos / 249.063.080 bytes, incluindo todos os originais,
archives/artifacts, journals, relações, materialização e bundle. Arquivos grandes
não foram adicionados ao Git. Inventários/hashes/scripts/relatórios e quatro
capturas são versionados. [files.json](inventory/files.json) enumera tamanho/hash
de cada arquivo; [artifact-hashes.json](inventory/artifact-hashes.json) reproduz o
manifesto operacional. SHA-256 de `SHA256SUMS.json`:
`3ccd41b172dd23724cb6a622a05a41e22843779847073a230976d926bc627774`.

As duas árvores foram lidas integralmente e seus hashes conferiram. Com a raiz
principal temporariamente renomeada, a segunda cópia passou nos readers públicos
de materialização e bundle. Nenhum arquivo histórico foi movido/apagado.
[Prova de independência](backup-verification.json). Um ensaio adicional restaurou
exclusivamente pelo backup para destino novo, sem banco/receipts novos, conferiu
todos os hashes e ambos os readers e gerou config externa nova:
[restore-drill.json](restore-drill.json), [script](restore.py).

A cópia bruta do archive em path diferente é recusada porque `archive_root` integra
o receipt aceito. Essa contraprova esperada expôs um excesso do primeiro wrapper,
não defeito do writer/reader. Ela está registrada e não foi contornada. O bundle
e a materialização autocontidos são portáveis; restaurar o archive bruto para
`recover()` exige seu path nominal original livre, sem sobrescrever sobreviventes.
[Procedimento e restrição](README.md). Duas cópias no mesmo disco protegem da perda
de temporários, não da perda do disco; não se anuncia recuperação de desastre.

A primeira tentativa, com formato inválido de derivedAt na projeção, também foi
preservada em ambos os destinos com run-id `20261019T024021Z-890e233c`, junto do
cluster desligado e diagnóstico. A segunda carga/projeção passou; seu comando
terminou com código 1 somente na contraprova adicional de archive relocável.
A continuação de preservação/restauração passou sem repetir carga ou criar receipts.
Esses fatos não foram apagados dos registros.

## Laboratório, HTTP e visual reais

[Configuração REAL_ARCHIVE](lab-config.json), apontando o bundle principal fora
de web-ui. Pin efetivamente conferido:
`sha256:2fae3be2b1ab7e5799287469ec29b9a98ff652a365ccafcb11b46c55d98ace8a`.
Label explicita 2026 W1/W2/W1–2, NE POST2025 e lacuna BAL W3; não é atualização corrente.
Sessão real:
`sha256:a0b4a5b4ffbac39ef3ea827c1c7b0b53a30156aa1a94214da3722630dd3d9e2c`.

[HTTP real](http.json): 48 respostas conferidas integralmente contra reader → DTO,
catálogo/identidades e 11 recusas de transporte. [Chrome](evidence/browser.json):
48 recortes selecionados e frações visíveis, papel/denominadores, EPA/sucesso
permitidos na defesa, volume/frequência, POST separado, BAL W3 sem zero, UNKNOWN,
reload/persistência da escolha, detalhes por Enter/Space/foco e uma observação por
vez. Desktop 1440×1000 e mobile 390×844, sem overflow horizontal. Chrome próprio
headless 155.0.8059.82, fechado ao final.

Capturas abertas e inspecionadas:
[ataque BAL W1–2](evidence/desktop-bal-w1-w2.png),
[defesa DAL passe W2](evidence/desktop-dal-defense-pass-w2.png),
[NE POST2025 mobile](evidence/mobile-ne-post2025.png),
[lacuna BAL W3 mobile](evidence/mobile-bal-w3-gap.png).
Exemplos: BAL geral W1–2 EPA `25.678661890850767072/115`, sucesso `65/115`;
DAL defesa passe W2 EPA permitido `1.212177313656378383/35`, frequência `35/67`.
Nenhum sinal defensivo foi invertido. BAL W3 conserva totals/valores null.

[Lifecycle real](lifecycle-02/lifecycle.json): em cópia descartável, adulteração
no disco não mudou os bytes HTTP congelados; reinício revalidou e recusou a entrada,
respondeu 409 à sessão anterior e removeu a escolha sem fallback. Depois restaurou
somente a cópia descartável e revalidou os mesmos bytes/identidades/escolha.
Reinício de conteúdo idêntico conserva sessionId legitimamente. A primeira
localização e o backup reais nunca foram adulterados.

[Seis contraprovas](counterexamples.json): EPA inventado com IDs/hashes externos
recalculados, dependência ausente, campo obrigatório removido com rehash, limitação
obrigatória removida com rehash, extrato isolado e pin errado. Todas recusadas em
cópias descartáveis. O 409 de ciclo de vida é a sétima contraprova solicitada.
Não houve participantes/protocolo de compreensão humana ou certificação de UX.

## Verificações, encerramento e limites

- 303 pytest: 220 de lab/projeção/materialização/persistência/pipeline/auditor,
  mais 83 do adapter; sem falhas/skips finais.
- 17 testes E5c-1 no Python 3.14/jsonschema já existentes; schema dos 48 documentos
  reais aprovado; 26 exemplos E5a aprovados. Nenhum main histórico/gate foi ajustado.
- 133 testes frontend, lint e build aprovados. Cinco expected-failure legados
  continuam preservados. [Logs](tests/).
- SQL real, duas execuções completas locais e reconciliação independente passaram.
  As 51 regressões SQL históricas e Java não foram repetidas: componentes iguais,
  nenhum uso Java nesta cadeia; não se reivindica uma nova execução dessas suítes.
- `git diff --check` e preservação da base/código/arquivos históricos aprovados.
- [Encerramento](shutdown.json): ambos os clusters próprios com pg_ctl=3,
  postmaster PID ausente, containers exited/PID 0; portas 50049, 50101 e 18083
  sem listener e com bind livre. PIDs dos três servidores de lifecycle ausentes;
  Chrome próprio fechado. Containers/serviços históricos continuam inalterados.

Completude, expectativa de cobertura, modelo EPA, disponibilidade/ingestão
histórica e encerramento continuam UNKNOWN. Persistência atual não demonstra
conhecimento passado. Sem comparação, pregame, novas métricas, processo semanal,
modelos, snapshots/aprovações, merge em main, push ou deploy. Supabase completo/
advisors, compreensão humana, BASIC/FULL e defeitos legados seguem pendências
separadas. Não há bloqueio de runtime/bind/browser nesta candidata.

Os comandos para leitura, restauração, laboratório, contraprovas e nova carga
estão no [README](README.md). Um checkout novo recupera scripts/evidências;
repetir a prova real exige os quatro bytes locais ou as cópias completas preservadas.
Hashes versionados não substituem esses arquivos.
