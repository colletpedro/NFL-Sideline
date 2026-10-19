# Aceite E5c-3R — dados reais e recuperação durável, 19/10/2026

Aceita após revisão independente e correção do preflight da restauração.
Candidata `b2e439fa73abf595968a96cd09066c2555f1dd5d`, base
`ce06a6291d1a2e935871fef04f543a54489755f5`, integrada em
`codex/metrics-integration-e5c3r`. A candidata e seus relatórios são preservados.

## Correção de revisão

O restore.py candidato checava destinos novos e disjuntos entre si, mas permitia
destino/configuração/relatório dentro da árvore de backup. Isso poderia copiar
uma árvore para dentro dela mesma ou escrever no backup depois de conferi-lo.
As três contraprovas foram demonstradas com cópia **mockada**, sem executar cópia
recursiva nem alterar dados reais. [Antes](guard-before.json).

A correção `23a48e8` exige que os três destinos também sejam disjuntos do backup
e reutiliza safe_path para recusar aliases por symlink e `..`, antes de ler ou
copiar. **Nove testes novos** cobrem os três destinos internos, aliases, `..` e
preflight válido. [Testes](test_restore_guard.py). O leitor/adapter/contratos e
os bundles não foram alterados.

Reprodução dos nove casos, na raiz com o venv ETL existente:

```sh
PYTHONPATH=etl-pipeline/src PYTHONDONTWRITEBYTECODE=1 \
  etl-pipeline/.venv/bin/python -B -m pytest -p no:cacheprovider \
  docs/plans/metrics/e5c-3r-review/test_restore_guard.py -q
```

## Verificação de artefatos e recuperação

As duas cópias originais foram lidas integralmente: **162 arquivos e 249.063.080
bytes por cópia**, hashes idênticos e manifesto conferido. A leitura pelo backup
passou com builtins.open/io.open impedindo leitura de arquivos da raiz principal;
nenhuma leitura proibida foi tentada. Isso testa independência de leitura dos
bytes, sem renomear ou indisponibilizar fisicamente o diretório histórico.
[Verificação](backup.json).

Foi executado o restore.py corrigido em um terceiro destino novo e durável:
`editorial/local-artifacts/real-recovery/review-20261019-orchestrator/` no checkout
original. A cópia contém os mesmos 162 hashes, passou nos leitores públicos e
gerou configuração externa em
`editorial/local-artifacts/operations/review-20261019-orchestrator/lab-config.json`.
Sem banco, novos receipts ou nova derivação. [Restauração](restore.json).

O auditor independente E5b-6 releu os quatro Parquets preservados e reconciliou
com a extração SQL arquivada: **557 associações e 3.804 grupos**, com somas e
denominadores exatos. [Auditoria](audit.json). A revisão não repetiu a carga
PostgreSQL nem a idempotência em banco: essas provas são da candidata. Seus
wrappers, registros, identidades e linhagem foram revisados; os 161 hashes de
componentes aceitos conferiram. Os dois containers identificados da candidata
foram consultados apenas em leitura: ambos exited/PID 0, sem iniciar serviços.

## HTTP e Chrome independentes

O laboratório foi iniciado sobre a **terceira cópia restaurada**. Reproduzidos:

- **48 documentos reais e 11 recusas HTTP**, com igualdade completa reader → DTO,
  IDs, denominadores, UNKNOWN e lacuna BAL W3. [HTTP](http.json).
- Chrome headless próprio, Playwright e runtimes existentes: **48 recortes**,
  frações visíveis, defesa, referência POST2025, seleção, reload, teclado/foco,
  details, desktop 1440×1000 e mobile 390×844 sem overflow. [Browser](browser.json).
- Em cópia descartável: bytes congelados após adulteração em disco, recusa no
  reinício, **409** à sessão antiga, escolha removida sem fallback e retorno aos
  mesmos bytes/identidades após restaurar a cópia descartável. [Ciclo](lifecycle.json).
- Seis contraprovas sobre cópias descartáveis, com rehash quando aplicável,
  recusadas. [Resultados](negatives.json).

Capturas próprias abertas e inspecionadas:
[BAL W1–2](evidence/desktop-bal-w1-w2.png) e
[BAL W3 ausente](evidence/mobile-bal-w3-gap.png). A captura própria NE POST2025
também foi inspecionada; fica na evidência operacional durável.
Não houve participantes ou avaliação de compreensão humana. Testes de teclado
e layout não constituem certificação completa de acessibilidade.

Todos os servidores e o Chrome próprios encerraram; PIDs ausentes e porta 18083
livre por bind. [Encerramento](shutdown.json). Não se parou container/serviço
histórico. Os relatórios completos e demais capturas próprias foram copiados para
`editorial/local-artifacts/operations/review-20261019-orchestrator/review-evidence/`;
as evidências selecionadas estão versionadas neste pacote.

## Testes e preservação

Reproduzidos **303 pytest existentes**, **nove novos testes de restauração**,
**17 testes E5c-1**, **26 exemplos E5a**, schema dos **48 documentos reais**,
**133 testes frontend**, lint e build. Cinco expected-failure legados permanecem.
303 pytest não significa 303 testes PostgreSQL; as suites são offline.
SQL live/Java e o build com VITE_* hostis não foram repetidos nesta revisão,
porque os respectivos componentes permanecem iguais e o isolamento público
já foi verificado na revisão E5c-3.

As duas cópias originais e a terceira foram rechecadas após as contraprovas:
162 hashes idênticos nas três, inclusive o manifesto. Os 40 arquivos históricos
não rastreados e os componentes aceitos foram preservados. A única correção de
código incide no wrapper novo restore.py, documentada no README; não houve
alteração de fórmulas, schema, front-end, reader/projetor ou políticas temporais.
[Verificação e hashes](verification.json).

## Limites e próximo passo

Bundle aceito: `sha256:2fae3be2b1ab7e5799287469ec29b9a98ff652a365ccafcb11b46c55d98ace8a`.
Materialização: `sha256:f7a70f61b442d8d631e858ac05c5c6191652b8d0ed0ffd5a7ac8094939a8d3fa`.
Receipts/tempos atuais são da reconstrução; não conhecimento histórico.
Archive bruto conserva restrição de root; bundle/materialização são portáveis.
As três cópias locais não protegem de perda do disco. Não houve aquisição,
modelo, banco remoto, .env, atualização corrente, comparação, pregame, processo
semanal, publicação, push, merge em main ou deploy.

**O gate de dados reais da integração E5c-3 está fechado no escopo local.**
Completude, modelo EPA, expectativa e conhecimento histórico continuam UNKNOWN.
A próxima frente é apresentação/produto: reduzir o texto e os detalhes técnicos
antes dos números, melhorar a hierarquia visual e avaliar compreensão com os
recortes reais. Preservar limites próximos dos dados, sem inventar permissões
de comparação. BASIC/FULL, defeitos legados, Supabase completo/advisors e rollout
público continuam pendências separadas.
