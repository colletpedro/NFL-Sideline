# Diagnóstico temporal e calibração — v2

**Estado A: diagnóstico concluído e M3 congelado; avaliação independente pendente.** A constante recente corrige a maior parte da superestimação da v1. M3 acrescenta ganho retrospectivo modesto sobre ela.2025/2026 W1–7 são conhecidos. Não há promoção ao produto ou ranking de decisão.

[Relatório](REPORT.md) · [Auditoria](DRIFT-AUDIT.md) · [Protocolo](EXPERIMENT-PROTOCOL.md) · [Reserva](RESERVED-EVALUATION.md) · [Model card](MODEL-CARD.md) · [Passagem](HANDOFF.md) · [Figuras](figures/README.md).

## Código, base e fontes

Worktree gerenciada: `/Users/pedrocollet/.codex/worktrees/qb-risk-temporal-calibration-v2/NFL Sideline`; branch `codex/qb-risk-temporal-calibration-v2`, criada de `d654bd65f834f3903006a97b3074123eda26d236`. Código novo somente em `research/qb_risk_temporal_v2`; reutiliza o código v1 sem editá-lo. Os docs v1 são evidência histórica preservada.

Store durável:
`/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-temporal-calibration-v2/20261104-v2`.

- `inputs/v1/{raw,documentation,sources.json,development-v3}`: cópia verificada das fontes/primeiro freeze; os originais não foram alterados.
- `additional-sources.json`, `provider-revision-source.json`: roster semanal2026, documentação oficial/histórico e seus hashes. Nenhum novo PBP/FTN foi adquirido nesta rodada.
- `reference-v1/`: replay integral da v1 com seu pipeline. `reference-v1-check.json`:84 arquivos científicos idênticos.
- `experiment-verified/`: dataset lido da referência, diagnósticos, modelos, previsões por passe, splits por chave/candidato/ano, CIs, classificação de posição e decisão. `models/` preserva M1/M2/M3 por ano para auditoria, sem ampliar os candidatos. `frozen/` contém apenas M0/M1 e o M3 escolhido para reserva.
- `figures-verified/`: PNG/SVG e tabela de suporte das curvas.
- `reproduction-final/`: reconstrução offline em destino novo. A primeira comparação conservada difere em4SVGs por estado global de hash do renderer v1; `figures-rechecked/` e `reproduction-check-rechecked.json` registram a correção/rechecagem gráfica, com os outros resultados preservados.
- `reserved-status.json`: recusas prematuras reais, sem rótulos abertos ou aquisição futura.
- `wheelhouse/`, `requirements.lock`: instalação offline na plataforma atual CPython3.11/macOS arm64.
- Cópia de recuperação em `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/backups/qb-risk-temporal-calibration-v2/20261104-v2`, com receipt/hashes em evidence. Não é backup do venv: as wheels permitem recriá-lo.

Arquivos pesados permanecem fora do Git. `evidence/` traz JSON/CSV e modelos pequenos para revisão; não substitui o store. Models JSON transparentes, sem pickle/joblib. Não carregar artefatos não confiáveis como produção. Fontes FTN e figuras derivadas: **FTN Data via nflverse, CC BY-SA4.0**, transformadas, sem endosso. Condições de distribuição/limites da [NOTICE v1](../qb-interception-risk-baseline-v1/NOTICE.md) preservados; não presumir permissão irrestrita para publicar derivados. Não houve publicação.

## Ambiente e aquisição explícita

Na raiz da worktree:

```sh
python3.11 -m venv research/qb_risk_temporal_v2/.venv
STORE='/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-risk-temporal-calibration-v2/20261104-v2'
PY='research/qb_risk_temporal_v2/.venv/bin/python'
research/qb_risk_temporal_v2/.venv/bin/pip install --no-index --find-links "$STORE/wheelhouse" -r research/qb_risk_temporal_v2/requirements.lock
```

Outra plataforma exige wheels compatíveis; não garantimos identidade entre BLAS/plataformas. Se necessário instalar online, use o mesmo lock em ambiente isolado. Nenhum comando requer `.env`, banco, Gemini ou serviço pago.

Aquisição inicial somente de roster/documentação, reutilizando fontes v1 (destino novo):

```sh
$PY research/qb_risk_temporal_v2/prepare.py \
  --v1-store '/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/qb-interception-risk-baseline-v1/20261104-v1' \
  --store "$STORE"
```

No store existente, confere hashes e não atualiza arquivos. A v1 foi reexecutada antes de qualquer comparação v2. Os comandos completos dessa referência estão na [v1](../qb-interception-risk-baseline-v1/README.md); o wrapper completo abaixo a reconstrói automaticamente. Correção documental oficial FTN também congelada em `inputs/provider/dictionary_revision_detail.json` e manifest separado.

## Execução retrospectiva conhecida

```sh
$PY -W error::RuntimeWarning -W error::FutureWarning research/qb_risk_temporal_v2/run.py \
  --store "$STORE" --out "$STORE/my-experiment-new"
$PY -W error::RuntimeWarning -W error::FutureWarning research/qb_risk_temporal_v2/figures.py \
  --experiment "$STORE/my-experiment-new" --out "$STORE/my-figures-new"
```

Destinos existentes são recusados. São quatro candidatos predefinidos, sem nova busca de regularização. O wrapper bloqueia conexões Python. Dados conhecidos2026 W1–7 não entram na escolha, e qualquer semana2026 fora dessa faixa é recusada por `known_only`. Não modificar protocolo/código de previsão depois de abrir reserva.

## Reprodução completa offline

```sh
$PY -W error::RuntimeWarning -W error::FutureWarning research/qb_risk_temporal_v2/reproduce.py \
  --store "$STORE" --out "$STORE/reproduction-review-new"
```

Reconstrói população/SQLite independente/splits/treinos/previsões v1 com o pipeline original; compara seus84 hashes; refaz v2 no replay novo, figuras e comparação de todos os artefatos científicos com a execução congelada. Rede explicitamente bloqueada. Recibos distinguem igualdade de bytes de equivalência numérica. Esta plataforma reproduziu124 arquivos científicos byte a byte após corrigir o estado gráfico; `environment.json` é excluído por registrar inventário/hash de código e diferenças de ambiente esperadas, nunca usado para ocultar diferença de previsões. Tolerância numérica prevista para investigação: atol1e-12/rtol1e-10, sem chamá-la de identidade de bytes.

Se for preciso repetir somente figuras, preservar saída anterior, usar outro diretório e revalidar a comparação:

```sh
$PY research/qb_risk_temporal_v2/figures.py --experiment "$STORE/reproduction-final/experiment" --out "$STORE/reproduction-final/another-figures-new"
$PY research/qb_risk_temporal_v2/reproduce.py --store "$STORE" --out "$STORE/reproduction-final" --verify-existing --figures-dir another-figures-new
```

O verificador preserva a primeira comparação. Não sobrescrever recibos existentes. Para nova revisão normal, prefira sempre o wrapper completo em destino novo.

## Avaliação futura: atualmente bloqueada

```sh
FREEZE="$STORE/experiment-verified/frozen"
$PY research/qb_risk_temporal_v2/reserved.py preflight --freeze "$FREEZE"
```

Resultado atual esperado: exit3/PREMATURE. Reserva **2026 REG W9–13**; a W8 foi excluída por exposição agregada prévia na v1. Piso operacional atual: **15/12/2026 às22h15 de Fortaleza** (16/12 01:15 UTC), sujeito a adiamentos. Sem espera ativa ou automação.

Somente após maturidade, adquirir cópias públicas próprias em destino novo:

```sh
$PY research/qb_risk_temporal_v2/acquire_reserved.py \
  --freeze "$FREEZE" --out "$STORE/reserved-sources-new"
$PY research/qb_risk_temporal_v2/reserved.py evaluate \
  --freeze "$FREEZE" --manifest "$STORE/reserved-sources-new/manifest.json" \
  --out "$STORE/reserved-evaluation-once"
```

A aquisição checa o piso antes de rede, baixa calendário atualizado e exige todos os jogos completos antes dos Parquets; pin de URLs/instantes/hashes/licenças. A avaliação exige manifest ligado ao SHA do freeze, roles exatos schedule/PBP/FTN, aquisição posterior à margem de maturidade e não futura, calendário sem mudança de universo/semana, hashes de contratos/código/modelos e join 1:1 com todos os jogos/labels da população. Nenhum argumento permite fingir data futura. Arquivos sazonais podem conter outras semanas, mas somente W9–13 entra na avaliação. Falta de label/jogo/identidade aborta; nenhum resumo parcial é emitido. `OPENED.json` no bundle impede repetir a abertura; manter esse recibo se algo falhar e diagnosticar sem tunar. Não copiar o bundle para contornar a abertura única. Use os originais operacionais do store, não a cópia de revisão versionada, para conservar o recibo.

Em caso de falha após abertura, preservar fontes, modelo, recibo e erro; recuperar somente a mesma execução/manifest após diagnóstico, com procedimento revisado explicitamente, nunca alterar candidato ou escolher uma subjanela favorável. O comando automatizado recusa reabertura por padrão.

## Testes e isolamento

```sh
$PY -W error::RuntimeWarning -W error::FutureWarning -m pytest research/qb_risk_temporal_v2/tests research/qb_interception_risk/tests -q
npm --prefix web-ui test -- src/components/visual-preparation-regressions.test.tsx
$PY research/qb_risk_temporal_v2/isolation.py --out "$STORE/isolation-review-new.json"
```

Fixtures offline, sem downloads. Se necessário, `npm --prefix web-ui ci` somente nesta worktree. Checagens incluem cronologia/IDs de jogos, reserva fora da seleção, intercepto separado, preprocessing só no treino, zero eventos, identidade/posição desconhecida ou conflitante, manifests adulterados, recusa prematura antes de abrir Parquets/rede e imutabilidade v1. Isolamento confere os347 arquivos pinados da v1, HEAD/status dos dois checkouts preservados, árvore operacional e cinco expected failures. Nenhuma auditoria visual do site foi repetida.

[Verificação](evidence/verification.json), [replay](evidence/reproduction-check.json), [isolamento](evidence/isolation.json), [recuperação](evidence/recovery-receipt.json). Commits/checkpoints: [CHECKPOINTS](CHECKPOINTS.md).
