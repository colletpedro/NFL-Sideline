# Produção dos quarterbacks na progressão e em improvisação · v1

Pesquisa descritiva concluída, **sensível à definição**, preparada para revisão antes de integração. 69.505 dropbacks REG 2023–2026, com 2022 separado; todas as categorias e casos preservados. Nenhuma interface, pacote ativo, ponteiro M3/B2 ou servidor foi alterado. Sem merge, push, deploy, publicação, Gemini, credenciais ou serviços pagos.

[Relatório com resultados e exemplos](REPORT.md) · [contrato congelado](RESEARCH-CONTRACT.md) · [classificação](CLASSIFICATION.md) · [auditoria](DATA-AUDIT.md) · [cartão da métrica](METRIC-CARD.md) · [figuras PNG/SVG](figures/README.md) · [tabelas completas](tables/comparisons.csv) · [handoff](HANDOFF.md).

## Repositório e pacote

Worktree: `/Users/pedrocollet/.codex/worktrees/qb-structure-production-v1/NFL Sideline`.
Branch: `codex/qb-structure-production-v1`, base `01f23cfc64fee10f5b16dafae7eb4dabeff8579c` (ancestral confirmado), contrato inicial `9b5fecb`.

Store durável local, fora do Git:
`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-structure-production-v1/20261105-v1`.

- `sources/`: 20 fontes próprias copiadas e verificadas, manifest pai e documentação/licença.
- `package-release/`: **única saída candidata de consumo**, versão 1.0.0, 257 arquivos manifestados, 199 detalhes GSIS, 89.715 linhas elementares (69.505 principais + 20.210 de auditoria 2022). [Índice para revisão](evidence/package-index.json) · [manifest/hashes](evidence/package-manifest.json).
- `recovery-final/frozen-sources-and-code.tar.gz`: fontes e núcleo científico congelados, extração verificada; reprodução efetivamente executada a partir de `recovery-final/restored/sources`.
- `runtime/wheelhouse`: 23 wheels copiados após conferir o manifest anterior; `runtime/environment` é ambiente novo instalado **sem rede**, com as seis dependências diretas pinadas em `research/qb_structure_production/requirements.txt` e transitivas resolvidas localmente.
- `reproduction-final/` e `reproduction-independent-env/`: reconstruções em destinos novos, incluindo figuras e auditoria independente SQL.
- `update-replay/`: atualização com fontes congeladas e classificação fixa, zero adições/remoções/revisões.
- `delivery-final/frozen-delivery.tar.gz`: recuperação final de fontes, pacote, código, documentos e wheels; [recibo de extração e hashes](evidence/delivery-recovery.json). Armazenamento local verificado; não é alegação de backup remoto.

As saídas `package/` (interrompida antes de agregar), `package-v1/`, `package-final/` e tentativas de figuras são desenvolvimento preservado, **não** pacotes ativos. A primeira interrupção ocorreu por colisão de nome `games`; corrigida antes da saída de consumo, sem mudar população/regras. A primeira figura falhou por indexação de Series e foi regenerada; a identificação de dois pontos próximos foi ajustada sem deslocar coordenadas. Esses registros não substituem `package-release`.

## Reprodução offline já verificada

Na raiz da worktree, sempre em **destino novo**:

```sh
QB_STORE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-structure-production-v1/20261105-v1'
QB_PY="$QB_STORE/runtime/environment/bin/python"

"$QB_PY" -m pytest research/qb_structure_production/test_structure.py -q

"$QB_PY" research/qb_structure_production/reproduce.py \
  --sources "$QB_STORE/recovery-final/restored/sources" \
  --reference "$QB_STORE/package-release" \
  --out "$QB_STORE/reproduction-review-NEW" \
  --receipt "$QB_STORE/reproduction-review-NEW.json"
```

`reproduce.py` bloqueia os pontos de entrada de rede, confere hashes fixos de código/contrato, valida fontes, reconstrói categorias/agregados/detalhes/exemplos/figuras, verifica todos os arquivos e reconcilia os brutos via SQLite. Não baixa dados em testes. Não precisa de banco, backend, Vite, arquivo `.env` ou modelos existentes.

Na reprodução realizada, **256/257 arquivos foram byte a byte idênticos**. Só `index.json` difere porque registra o caminho absoluto do manifest da fonte recuperada; o manifest de saída consequentemente também muda. Todas as tabelas científicas são equivalentes a 1e−12 absoluto, linhas elementares exatas e PNG/SVG idênticos. [Recibo](evidence/reproduction-independent-env.json) · [SQL independente da reprodução](evidence/reproduction-independent-env.sql.json). Identidade de bytes e equivalência numérica são verificações distintas.

Para reconstruir o ambiente sem rede, usar outro path inexistente para o venv:

```sh
python3.11 -m venv "$QB_STORE/runtime/review-env-NEW"
"$QB_STORE/runtime/review-env-NEW/bin/python" -m pip install \
  --disable-pip-version-check --no-index \
  --find-links "$QB_STORE/runtime/wheelhouse" \
  -r research/qb_structure_production/requirements.txt
```

[Instalação offline realizada](evidence/offline-install.log) · [42 testes no ambiente novo](evidence/tests-complete.log). O ambiente mínimo de pesquisa não inclui sklearn, necessário apenas ao legado; regressões preservadas foram executadas em seu ambiente completo: M3 23, B2 33, pacote do laboratório 6, todos aprovados. A tentativa inicial de B2 no ambiente mínimo falhou na coleta por dependência ausente e está registrada separadamente; não houve alteração no legado.

## Atualização manual, com regras fixas

Para atualizar 2026 por aquisição pública própria, o comando abaixo cria outra revisão, valida, classifica, agrega, gera figuras/pacote, verifica e reconcilia. Não toca nenhum ponteiro ativo. Requer rede somente para adquirir fontes públicas gratuitas. Não foi necessário adquirir novamente nesta entrega.

```sh
"$QB_PY" research/qb_structure_production/update.py \
  --source '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-expected-interceptions-v1/20261105-v1' \
  --season 2026 \
  --fixed "$QB_STORE/package-release/fixed.json" \
  --previous "$QB_STORE/package-release" \
  --out "$QB_STORE/update-YYYYMMDD-NEW"
```

O histórico é recopiado após verificação do manifest; atualiza PBP/FTN/schedule/roster 2026 em destino novo. Cada fonte tem URL, instante, headers, tamanho e SHA-256. `revision.json` registra chaves adicionadas/removidas e campos alterados com antes/depois. Revisão não apaga a anterior. Divergência do hash fixo de código/contrato aborta antes da aquisição; outra temporada exige revisão explícita do contrato de fonte.

Para replay sem rede, acrescentar `--frozen-sources "$QB_STORE/sources"` e usar outro `--out`. Isso foi executado; [zero mudanças e pacote anterior intacto](evidence/update-replay.json). Teste de ponta a ponta também altera EPA em uma cópia de fonte sintética, refaz hashes, verifica a revisão registrada e a preservação dos bytes anteriores.

## Recuperação e preservação

[Recibo de recuperação do núcleo](evidence/recovery.json) · [recuperação final completa](evidence/delivery-recovery.json) · [resumo de preservação](evidence/preservation-summary.json). O pacote é completo quando há manifest e verificação bem-sucedida; diretório parcial nunca é ativado. Nenhum mecanismo de publicação foi adicionado.

[Fontes](evidence/sources.json) · [contrato público preservado](../../static-snapshot-contract.md) · [contrato interno de pacote](HANDOFF.md). FTN Data via nflverse, dados transformados sob CC BY-SA 4.0, sem endosso. Fontes restantes conforme licença pinada; não há publicação externa nesta entrega.

A URL de referência 18125 não respondeu na checagem inicial nem final; `curl --noproxy` confirmou conexão recusada e `lsof` não encontrou listener. Nenhum servidor foi reiniciado para esta pesquisa. A preservação demonstrada é dos arquivos/stores/estado do checkout, não uma certificação de disponibilidade da prévia. [Recibo](evidence/server-availability.json).
