# Pesquisa — interceptações sofridas em relação ao risco dos passes

**Concluída para revisão em 05/11/2026. B2 escolhido; sem ganho contextual convincente e com limite de calibração em FTN=0 em 2025.** Aplicação atual: 121 jogos, W1–8, 7.970 passes, 170 INT observadas / 167,961706 esperadas. Não houve integração visual, ativação, merge, push, deploy ou publicação externa.

[Relatório](REPORT.md) · [Contrato anterior às comparações](RESEARCH-CONTRACT.md) · [Auditoria](DATA-AUDIT.md) · [Model card](MODEL-CARD.md) · [Passagem para integração posterior](HANDOFF.md) · [Figuras](figures/README.md) · [Contrato do consumidor](../../../research/qb_expected_interceptions/consumer-contract.json).

## Base e armazenamento

Worktree gerenciada: `/Users/pedrocollet/.codex/worktrees/qb-expected-interceptions-v1/NFL Sideline`.
Branch `codex/qb-expected-interceptions-v1`, base aprovada `5d7d7769ce71a6864edce4c7393a75913563595f`, conferida limpa. Repositório principal e laboratório aprovado preservados, inclusive alterações preexistentes do principal, M3, fontes pinadas, build público e servidor 18124. Mudanças somente em `research/qb_expected_interceptions/` e neste diretório.

Store próprio, fora do Git:
`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-expected-interceptions-v1/20261105-v1`.

| Diretório | Conteúdo |
| --- | --- |
| `raw/`, `lineage/` | Cópias verificadas dos PBP/FTN 2022–2025, manifest e dataset reconciliado anterior |
| `current/`, `rosters/`, `documentation/` | Aquisição própria 2026, roster semanal 2022–2026 e documentação/licenças |
| `previous-lab/` | Cópia verificada das fontes do laboratório para comparar revisão, sem alterá-las |
| `sources.json` | Manifest completo de aquisição/cópia, URLs, instantes, hashes, tamanhos, atribuição |
| `build/` | População, splits por passe, quatro cruzamentos, auditoria SQL independente, cobertura, revisão |
| `development/` | Pequena busca temporal, referências, modelos por fold, decisão e freeze original pré-2025 |
| `evaluation/` | 2025 fora do ajuste, todos os candidatos, previsões por passe, métricas/grupos/calibração/bootstrap/jogadores |
| `final/` | B2 JSON fixo, taxas de 2025 e manifesto/hash de inferência; sem pickle/joblib |
| `application-complete/` | Aplicação atual completa, tabela por jogador, previsões, casos e `consumer/` |
| `figures-reviewed/` | PNG/SVG revisados e tabelas de suporte |
| `reproduction-offline/` | Reconstrução offline completa em destino novo; recibo 156 arquivos científicos idênticos |
| `update-replay-sources/`, `update-replay/` | Prova de atualização somente por aplicação, sem fit, com revisão e reconciliação |
| `wheelhouse/`, `requirements.lock` | Ambiente recriável offline em CPython 3.11/macOS arm64 |

`application/` conserva a primeira tentativa, interrompida ao gravar casos por ausência do diretório; não é o pacote completo. `figures/` conserva a primeira revisão de layout. Usar somente `application-complete/` e `figures-reviewed/`. A correção de I/O é registrada em [output-fix](evidence/output-fix.json); não alterou seleção, parâmetros, features ou avaliação.

`evidence/` contém cópias pequenas para revisão, inclusive o índice de consumo, taxas fixas, métricas, casos e tabela de jogadores. Os Parquets/fontes/wheels pesados ficam no store e na cópia de recuperação. [Manifest do pacote](evidence/package-manifest.json) e [recibo de recuperação](evidence/recovery.json). Não substituir o store pelos CSVs de revisão.

## Ambiente sem serviços ou segredos

Todos os comandos partem da worktree nova:

```sh
cd '/Users/pedrocollet/.codex/worktrees/qb-expected-interceptions-v1/NFL Sideline'
STORE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-expected-interceptions-v1/20261105-v1'
python3.11 -m venv research/qb_expected_interceptions/.venv
PY='research/qb_expected_interceptions/.venv/bin/python'
"$PY" -m pip install --no-index --find-links "$STORE/wheelhouse" -r research/qb_expected_interceptions/requirements.lock
```

Não carregar `.env`; não precisa banco, Docker, Gemini, Vercel, FTN pago ou serviços pagos. Não se carrega modelo serializado externo; somente JSON transparente gerado pelo próprio código e verificado por SHA-256. Outra arquitetura/Python exige wheels compatíveis; não prometemos identidade bit a bit entre plataformas/BLAS/renderers.

## Reprodução completa offline

Usar destino **novo**:

```sh
"$PY" -W error::RuntimeWarning -W error::FutureWarning research/qb_expected_interceptions/reproduce.py \
  --store "$STORE" --out "$STORE/reproduction-minha-revisao-nova"
```

O comando bloqueia conexões Python antes de ler/reconstruir fontes; não instala nem baixa dados. Confere todos os hashes; reconstrói população e auditoria SQLite; refaz seleção/treinos; confronta todos os parâmetros e previsões; refaz 2025, refit B2, aplicação, agregados e PNG/SVG. Só após provar que a seleção/modelos recalculados são idênticos utiliza o freeze original para manter sua proveniência pré-2025. Não altera nenhum freeze antigo.

Resultado local: **156 arquivos científicos idênticos em bytes**. CSV/Parquet também são comparados numericamente com atol=1e-12/rtol=1e-10. `environment.json` é inventário e não entra nessa identidade. O novo `development/freeze.json` difere somente no hash do orquestrador pela correção de diretório de casos registrada; ambos são preservados e todo o restante do freeze deve ser igual. Não chamar isso de identidade integral do diretório nem de teste novo. [Recibo completo](evidence/reproduction.json).

## Atualização de dados sem retreino

O procedimento e as taxas estão fixos no `final/model.json`, hash `ebc588e7990e29fb2e5ba8848558c1e5948222d7a6f002f07575a66d38186db8`. Adquirir cópias públicas novas e aplicar somente esse modelo:

```sh
"$PY" research/qb_expected_interceptions/update.py \
  --final "$STORE/final" \
  --previous "$STORE/application-complete" \
  --out "$STORE/updates/minha-aquisicao-nova"
```

Esse comando adquire PBP/FTN/calendário/roster 2026, valida jogos encerrados individualmente, estima probabilidades com o JSON fixo e produz outro pacote em `application/` mais `revision.json`. **Não chama fit, não atualiza ponteiro, não muda laboratório e não exige semana completa.** O jogo com lacuna é identificado; os demais válidos entram. Contradições estruturais abortam. O pacote anterior permanece intacto, inclusive em falha. Diretórios existentes são recusados.

Reaplicar uma aquisição já pinada, sem rede, também não ajusta o modelo:

```sh
"$PY" research/qb_expected_interceptions/update.py \
  --sources "$STORE/update-replay-sources" \
  --final "$STORE/final" --previous "$STORE/application-complete" \
  --out "$STORE/updates/replay-novo"
```

Depois da atualização, inspecionar `coverage.json`, `sources.json`, `revision.json`, probabilidades e tabelas. Refit futuro é outra ação explícita de pesquisa; atualização não o provoca. Não há espera obrigatória por dezembro, nova janela de confirmação, servidor novo ou tarefa recorrente nesta entrega.

## Reconstruir etapas de pesquisa separadamente

A aquisição original pode ser verificada sem rede executando `acquire.py --store "$STORE"`; store existente só verifica hashes. Para nova aquisição integral, usar store novo: copiará os históricos verificados e obterá fontes atuais, sem substituir os originais. Fontes novas podem conter revisões e não equivalem à reprodução congelada.

```sh
"$PY" research/qb_expected_interceptions/acquire.py --store '/CAMINHO/NOVO'
"$PY" research/qb_expected_interceptions/run.py build --store "$STORE" --out "$STORE/review-build-new"
"$PY" research/qb_expected_interceptions/run.py develop --build "$STORE/review-build-new" --out "$STORE/review-dev-new"
"$PY" research/qb_expected_interceptions/run.py evaluate --build "$STORE/review-build-new" --development "$STORE/development" --out "$STORE/review-eval-new"
"$PY" research/qb_expected_interceptions/run.py refit --build "$STORE/review-build-new" --development "$STORE/development" --out "$STORE/review-final-new"
"$PY" research/qb_expected_interceptions/run.py apply --store "$STORE" --build "$STORE/review-build-new" --final "$STORE/review-final-new" --out "$STORE/review-app-new"
"$PY" research/qb_expected_interceptions/figures.py --evaluation "$STORE/review-eval-new" --application "$STORE/review-app-new" --out "$STORE/review-figures-new"
```

O exemplo mantém o freeze original para avaliação/refit após o replay de desenvolvimento, como o wrapper faz. Repetir 2025 não autoriza corrigir o teste. Se houver mudança estatística, criar outro contrato e versão, sem reescrever esta pesquisa.

## Testes e isolamento

```sh
"$PY" -W error::RuntimeWarning -W error::FutureWarning -m pytest research/qb_expected_interceptions/tests -q
"$PY" -W error::RuntimeWarning -W error::FutureWarning -m pytest research/qb_risk_lab/test_pipeline.py research/qb_interception_risk/tests research/qb_risk_temporal_v2/tests -q
"$PY" research/qb_expected_interceptions/isolation.py check \
  --before docs/plans/qb-expected-interceptions-v1/evidence/preservation-before.json \
  --out "$STORE/isolation-minha-revisao-nova.json"
```

33 testes novos e 59 preservados passaram. Rodar os grupos em processos separados: os legados usam módulos `common` homônimos; a tentativa conjunta de collection falhou por colisão de namespace e foi conservada em `evidence/tests.log`. Nenhum resultado foi contado como executado nessa tentativa. Testes novos bloqueiam rede e incluem join/cardinalidade, quatro cruzamentos, elegibilidade, alvo ausente, temporalidade, preprocessing só no treino, colunas proibidas, suporte/bordas, decomposição/sinal/unidades, GSIS/posição/troca de equipe, zero eventos/poucos passes, determinismo, modelo errado/M3, lacunas por jogo e prova de atualização sem fit.

Sem alteração no site, não repetimos auditoria visual nem compilação pública. A prova de isolamento confronta bytes das fontes/pesquisas/builds aprovados, HEAD/status dos checkouts preservados, mudanças Git somente no escopo autorizado e listener 18124. [Recibo](evidence/isolation.json).

Para nova cópia de recuperação, em destino disjunto novo:

```sh
"$PY" research/qb_expected_interceptions/archive.py --store "$STORE" \
  --backup '/CAMINHO/DE/RECUPERACAO/NOVO' --receipt '/CAMINHO/RECIBO-NOVO.json'
```

FTN Data via nflverse, CC BY-SA 4.0; fontes transformadas, sem endosso. Outras fontes conforme manifest. A atribuição e a limitação de charting retrospectivo acompanham as figuras e o pacote. Não presumir direitos irrestritos de publicação dos derivados.

A cópia de recuperação desta entrega contém **565 arquivos / 295,122,487 bytes**, todos revalidados por SHA-256, em `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/backups/qb-expected-interceptions-v1/20261105-v1`. Para recuperar sem os caminhos originais, copie essa árvore para um destino novo e disjunto, use o código desta branch, recrie o venv pelos wheels da cópia e execute:

```sh
RESTORED='/CAMINHO/DA/COPIA/RESTAURADA'
"$PY" research/qb_expected_interceptions/reproduce.py --store "$RESTORED" --out "$RESTORED/reproducao-restaurada-nova"
```

Os paths dos arquivos no manifest são relativos ao store. A reprodução usa as fontes copiadas, sem depender dos paths originais v1/v2/laboratório e sem rede. O código e a documentação precisam acompanhar o checkout desta branch; o backup não contém venv ou credenciais.
