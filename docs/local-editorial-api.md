# API editorial local restrita — 1.1.0

`editorial-local-serve` inicia exclusivamente um HttpServer do JDK em `127.0.0.1`.
Não inicia Spring, datasource, repositórios JPA, Gemini ou exportador. As classes locais
não são componentes Spring: os modos normal e snapshot não registram essas rotas.
O caminho Gemini, prompts, cache e endpoints anteriores permanecem intactos.

`LocalGenerationService.generate(AnalysisContext, EditorialParameters, ClaimSelector)`
executa seleção, validação comum e renderização, nessa ordem. Retorna textos tipados,
seleção completa e identidade. CLI e HTTP usam esse serviço. Não há provedor automático,
fallback ou revisão humana obrigatória.

Versões: serviço **1.0.0**, HTTP **1.1.0**, identidade **local-result-1**, artefato **3**.
Seletor **local-descriptive-rules 2.0.0**, entrada **3**, claims **5** e renderer
**controlled-claims-v5.0.2** (correção de apresentação das faixas próximas de zero). O artefato mudou para incluir identidade
estruturada e parâmetros, sem nova política editorial. NONE/INCONCLUSIVE, quatro textos
públicos e contratos anteriores permanecem preservados.

## Comandos

Da raiz, sem carregar `.env`. Antes de reconstruir um JAR congelado, preserve o pacote
histórico como descrito abaixo. Exemplo com caso já conhecido, sem download ou banco:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
mvn -f core-api/pom.xml -o clean verify
mkdir -p editorial/local-api-demo/contexts editorial/local-api-demo/results
cp editorial/evaluations/2026-09-26/contexts/2026_03_BAL_DAL.json editorial/local-api-demo/contexts/
env -i PATH="$JAVA_HOME/bin:/usr/bin:/bin" LANG=en_US.UTF-8 \
  "$JAVA_HOME/bin/java" -jar core-api/target/core-api-0.1.0.jar \
  editorial-local-serve editorial/local-api-demo/contexts editorial/local-api-demo/results 18081 \
  > editorial/local-api-demo/server.log 2>&1 &
local_editorial_pid=$!
```

Aguarde `LOCAL_ANALYSIS_READY` no log antes de gerar. A porta pode ser 0 para alocação
automática; o log informa a porta escolhida. Use diretórios novos para outro experimento.

```bash
curl --fail-with-body --noproxy '*' -X POST \
  http://127.0.0.1:18081/api/v1/local-analysis/2026_03_BAL_DAL \
  -o editorial/local-api-demo/response.json
attempt_id=$(python3 -c 'import json; print(json.load(open("editorial/local-api-demo/response.json"))["attemptId"])')
curl --fail-with-body --noproxy '*' \
  "http://127.0.0.1:18081/api/v1/local-analysis/2026_03_BAL_DAL/$attempt_id"
kill "$local_editorial_pid"
wait "$local_editorial_pid"
```

SIGTERM/Ctrl-C fecha servidor, executor e lock; o exit status de SIGTERM pode ser 143.
Não existe endpoint de desligamento. CLI anterior, mesmos argumentos e códigos 0/1:

```bash
java -jar core-api/target/core-api-0.1.0.jar editorial-local \
  editorial/local-api-demo/contexts/2026_03_BAL_DAL.json \
  editorial/local-api-demo/cli-attempt
```

A CLI exige pai existente e destino novo, recusando sobrescrita e diretórios públicos,
inclusive aliases via symlink. O servidor exige diretórios existentes e distintos, sem
conter um ao outro. Resultados que resolvam para componente `public` são recusados.

## Catálogo e protocolo

O catálogo é um diretório plano contendo somente arquivos JSON de contextos v3 válidos.
O ID vem de `game.game_id`, não do nome do arquivo. Duplicatas de ID, mesmo idênticas,
invalidam o catálogo. Symlinks, subdiretórios, entradas não regulares e contextos inválidos
impedem a inicialização. O conteúdo normalizado e hash da origem ficam congelados em
memória até reiniciar. Alterar arquivos depois não muda a geração corrente.

IDs aceitos: 1–128 caracteres ASCII alfanuméricos, underscore ou hífen. Não há caminhos,
contextos ou seletores escolhidos pelo cliente. Query string, percent-encoding, body,
Origin e Host diferente de `127.0.0.1:PORTA` são recusados. Não há CORS nem autenticação
entre usuários locais; é uma ferramenta restrita de desenvolvimento.

- `GET /api/v1/local-analysis/`: catálogo de metadados; datas são informações da origem, sem novo filtro temporal.
- `GET /api/v1/local-analysis/{gameId}/attempts`: histórico verificado e contagem global de entradas indisponíveis.
- `POST /api/v1/local-analysis/{gameId}`: body vazio; 201 e Location para consulta.
- `GET /api/v1/local-analysis/{gameId}/{attemptId}`: 200 e a resposta persistida.
- 400: requisição inválida; 404: contexto/resultado inexistente; 405: método/rota não
  suportado; 409: resultado incompleto/corrompido ou falha de geração/IO; 500: falha inesperada.

Erros contêm somente `{"error":"CODIGO_FIXO"}`, sem caminhos ou stack traces.
Envelope ilustrativo (não é evidência de HTTP real):

```json
{
  "mode": "LOCAL_RULES_DEVELOPMENT",
  "publicationApproved": false,
  "gameId": "2026_03_BAL_DAL",
  "attemptId": "<UUID>",
  "resultIdentity": "<SHA-256>",
  "analysis": {
    "fator_chave": "<texto>",
    "vantagem_tatica": "<texto>",
    "alerta_vermelho": "<texto>",
    "veredito": "<texto>"
  }
}
```

`analysis` tem exatamente os quatro campos. Claims e decisões ficam apenas nos arquivos
internos. Não se usa markdownText, identidade Gemini ou aprovação implícita.

## Identidade, repetição e arquivos

SHA-256 do JSON estruturado `Identity` inclui schema da identidade, SHA-256 do contexto
canônico, nome/versão do seletor, contrato, renderer e parâmetros (temporada, semana, fase).
A ordem dos campos é a declarada no record Java. A versão do serviço é registrada
separadamente; evolução incompatível da identidade exige outra versão do seu schema.

Cada POST executa novamente e reserva um UUID novo atomicamente. Repetições têm identidade
semântica igual e tentativas distintas. Não há cache, índice mutável de “último resultado”
ou sobrescrita. Seletores/versões distintos não compartilham identidade. Um lock exclusivo
impede dois proprietários simultâneos do mesmo diretório. Executor: 2–4 threads e fila de 32.

Em `results/{attemptId}/`: `context.json`, `selection.json`, `claims.json`, `rendered.json`
e `result.json`. Este último registra versões, identidade, parâmetros, hash da origem,
status e ausência de aprovação. `complete.json` contém resposta e hashes dos cinco arquivos;
é disponibilizado por rename atômico somente ao final. Filesystem sem ATOMIC_MOVE falha,
sem fallback não atômico. Consulta confere hashes, status e correspondência dos textos e
identidade. Resultados íntegros continuam consultáveis após reiniciar.

Falhas preservam a tentativa e, quando possível, `failure.json` com classe da exceção,
metadados e seleção rejeitada. Falha de disco pode impedir esse diagnóstico. Interrupção
pode deixar arquivos ou `complete.tmp`, mas nunca resultado parcial aceito. Não há limpeza
ou recuperação automática. O diretório deve ser controlado pelo operador; não é um volume
compartilhado com processos hostis. Hashes detectam corrupção, não são assinatura criptográfica.

## Baseline e limites

Os 138 hashes de `editorial/coverage-clarity-v1/freeze.json` foram conferidos antes de editar
ou reconstruir; todos os arquivos, incluindo o JAR, foram copiados para
`editorial/local-integration-v1/baseline/`. `baseline-lineage.json` registra a relação.
O congelamento histórico não foi reescrito. Fontes alterados e JAR novo **não** correspondem
a ele. O check histórico na árvore atual deve acusar essas mudanças. A integridade arquivada
e a identidade da implementação nova são verificadas separadamente no relatório da entrega.

Os 21 casos expostos são regressões, não avaliação independente. Aprovação mecânica não
comprova qualidade editorial. A validação operacional posterior verificou HTTP real, reinício e
apresentação no navegador; a faixa com desigualdade foi corrigida no renderer 5.0.2. Repetição de
nomes/avisos e extensão dos alertas permanecem limites editoriais, sem retuning nesta entrega.
O pacote original não incluía frontend. A [interface local de desenvolvimento](local-editorial-ui.md) agora usa um proxy restrito; não há publicação, migration, modelos ou dados novos nesta integração.

## Reprodução da validação operacional

Use diretórios novos. O teste inicia e encerra dois servidores Java em portas dinâmicas de
127.0.0.1; não carrega `.env`. Requer permissão de bind/conexão local no ambiente de execução.

```bash
python3 scripts/validate_local_operation.py editorial/validacao-operacional-nova
python3 scripts/build_operational_inspection.py \
  editorial/validacao-operacional-nova editorial/inspecao-operacional-nova
python3 scripts/serve_editorial_inspection.py \
  editorial/inspecao-operacional-nova/inspection.html --port 18082
```

Abra `http://127.0.0.1:18082/inspection.html`. Encerre o servidor de inspeção com Ctrl-C.
Ele serve somente o HTML indicado, sem disponibilizar os arquivos adjacentes. A página é uma
inspeção estática dos resultados persistidos, não um cliente que gera análises pela API.
Relatório: [validação operacional](../editorial/operational-validation-v1/REPORT.md).
