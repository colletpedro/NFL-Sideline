# Avaliação local de cobertura e clareza

Este documento registra a avaliação histórica do renderer 5.0.1. O estado atual e a correção
posterior das faixas em 5.0.2 estão em [current-state.md](current-state.md) e no
[relatório operacional](../editorial/operational-validation-v1/REPORT.md).

Renderer `controlled-claims-v5.0.1` corrige somente atribuição textual. No veredito cada grupo nomeia
ataque e defesa adversária; variação significa presença de semanas positivas e negativas, sem
inferir trajetória. Zeros continuam vinculados ao lado observado. Seletor 2.0.0, contrato 5,
EvidenceWindow, classificação, cobertura, agregações e interface permanecem idênticos. Claims v3/v4
conservam sua interpretação; artefatos do renderer 5.0.0 permanecem intactos, sem reescrita.

O censo desta entrega está em `editorial/coverage-clarity-v1/manifest.json`: 17 jogos reais distintos
(incluindo os seis conhecidos) e quatro sintéticos. Os 11 jogos adicionais têm geração anterior
comprovada no cache local preservado: **zero inéditos confirmados**. Ausência de contexto em um
manifesto não provaria novidade; o harness consulta também registros de execução/cache. Contextos
normalizados equivalentes são deduplicados. Não se fabricam entradas de textos publicados.

Protocolo registrado antes do lote: `editorial/coverage-clarity-v1/PROTOCOL.md`. O sidecar de calendário
usa somente schedules Parquet já locais, com checagem de completude, e não alimenta o seletor.
Indicadores separam seis regressões, 11 jogos adicionais com uso prévio e sintéticos. Nenhum desses
substitui avaliação independente. INCONCLUSIVE/NONE é requisito descritivo, não indicador de equilíbrio
ou falta de dados. Comprimento e repetição são exploratórios, sem nota de qualidade.

## Reproduzir a execução congelada

A partir da raiz, sem carregar `.env`. Java recebe ambiente mínimo; scripts usam somente arquivos.

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
python3 scripts/evaluate_coverage.py check editorial/coverage-clarity-v1
python3 scripts/evaluate_coverage.py run editorial/coverage-clarity-v1 --output editorial/coverage-clarity-v1/reproduction-01
python3 scripts/evaluate_coverage.py metrics editorial/coverage-clarity-v1 --run editorial/coverage-clarity-v1/reproduction-01 --output editorial/coverage-clarity-v1/reproduction-01-metrics.json
python3 scripts/evaluate_coverage.py html editorial/coverage-clarity-v1 --metrics editorial/coverage-clarity-v1/reproduction-01-metrics.json --output editorial/coverage-clarity-v1/reproduction-01.html
python3 scripts/evaluate_coverage.py check editorial/coverage-clarity-v1
open editorial/coverage-clarity-v1/reproduction-01.html
```

Todos os destinos devem ser novos. `run` verifica hashes antes/depois e mantém um diário exclusivo
por caso; uma falha não substitui ou apaga outra tentativa. Não reconstruir o JAR entre congelamento
e reprodução: um JAR com bytes diferentes falha na verificação. Uma reconstrução exige novo pacote
de congelamento e os casos já expostos não podem ser reclassificados como inéditos.

## Preparar outro pacote de avaliação

Criar diretório novo e protocolo antes do inventário. As entradas elegíveis são JSON v3 diretos;
Parquet bruto é inventariado, mas não convertido em novas métricas nesta entrega.

```bash
python3 scripts/evaluate_coverage.py inventory <pacote-novo>
etl-pipeline/.venv/bin/python scripts/export_local_calendar.py <pacote-novo>
mvn -f core-api/pom.xml -o clean verify
python3 -m unittest discover -s scripts -p 'test_evaluate_coverage.py' -v
etl-pipeline/.venv/bin/python -m unittest discover -s scripts -p 'test_local_calendar.py' -v
python3 scripts/evaluate_coverage.py freeze <pacote-novo>
python3 scripts/evaluate_coverage.py check <pacote-novo>
```

O exportador do calendário usa Polars **já instalado** no venv; não instala dependências. O teste do
harness usa artefatos conhecidos desta entrega como fixtures e deliberadamente não lê saídas dos
11 jogos adicionais. `known` é a suboperação de desenvolvimento que só admite os seis/sintéticos.
O manifesto congela hashes brutos e normalizados; `freeze.json` também congela fontes, testes,
documentos, harness, calendário e JAR. A normalização do inventário é separada do hash canônico Java.

## Métricas e inspeção

`metrics.json` contém denominadores, distribuições completas e verificações por claim. Cobertura
não é suficiência estatística. Casos sem oportunidade conservam os bloqueios de sinais e cobertura
simultaneamente; não se atribui causalidade única à cobertura. Mediana/p90/máximo são por coorte;
coorte vazia tem n=0 e estatísticas null. Repetição compara os seis pares de blocos, além de sentenças
normalizadas com cinco ou mais palavras. O método completo e seus limites constam do protocolo.

HTML autocontido usa fontes locais do sistema, CSP sem conexões e conteúdo escapado, quatro colunas
em telas largas, filtros e `<details>` nativo. Não há frontend de produção ou dependências novas.
Para checagem de fonte e lógica dos filtros, sem alegar inspeção visual:

```bash
node scripts/test_inspection_page.cjs editorial/coverage-clarity-v1/inspection.html
```

Testes estruturais não comprovam clareza plena; os detalhes permitem inspeção opcional e nenhuma
aprovação humana é exigida pelo comando de geração. A avaliação Gemini e os dados públicos não
participam da escrita. A revisão desta entrega é limitada; defeitos descobertos depois de congelar
são registrados, sem ajustes para melhorar o lote.
