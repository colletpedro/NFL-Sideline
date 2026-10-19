# Laboratório editorial local — 1.0.0

A página permite selecionar um contexto congelado, gerar por regras locais e recuperar tentativas imutáveis. Exibe os quatro textos do renderer sem reescrita no browser, o ID da tentativa e a identidade do resultado. Não prevê vencedor, não aprova nem publica análises. BASIC/FULL e avaliação editorial independente continuam pendentes.

## Iniciar

Da raiz do repositório, com Java 21, Maven e dependências frontend já instalados. Não carregar `.env`. Em um checkout novo, instalar as dependências normalmente antes do uso offline; “offline” descreve a geração, não o primeiro download de dependências de build.

Terminal 1:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
mvn -f core-api/pom.xml -o clean verify
mkdir -p editorial/local-interface-v1/runtime/results
env -i PATH="$JAVA_HOME/bin:/usr/bin:/bin" LANG=en_US.UTF-8 \
  "$JAVA_HOME/bin/java" -jar core-api/target/core-api-0.1.0.jar \
  editorial-local-serve editorial/evaluations/2026-09-26/contexts \
  editorial/local-interface-v1/runtime/results 18081
```

Terminal 2:

```bash
npm --prefix web-ui run editorial:dev
```

Abra **http://127.0.0.1:18083/**. Os 16 contextos desse exemplo são casos históricos conhecidos da Week 3, congelados em setembro; não representam atualização da semana atual. Outro diretório plano de contextos v3 pode ser escolhido ao iniciar a API.

As duas portas são fixas nesta interface (18081 API, 18083 UI); a UI falha se sua porta estiver ocupada. Use o endereço numérico indicado. Encerrar com Ctrl-C nos dois terminais. Reutilizar o diretório de resultados recupera as tentativas existentes; cada POST cria um novo UUID. O catálogo é congelado na inicialização: reinicie a API e recarregue a página após trocar os arquivos de entrada.

## Transporte e separação

A entrada `web-ui/local-editorial/index.html` tem configuração Vite própria, iniciada por `editorial:dev`, que desabilita a leitura de arquivos de ambiente (`envFile: false`). Não há importação dessa página em `src/App.tsx` nem no cliente de Production. O comando habitual de build continua usando somente a entrada pública estática. A configuração editorial recusa build e modo production; não serve `public/`.

Browser → `/__editorial/` no Vite 127.0.0.1:18083 → `/api/v1/local-analysis/` na API 127.0.0.1:18081. O destino é constante, sem variável pública ou URL fornecida pelo cliente.

Antes de encaminhar, o proxy verifica Host exato, Origin quando presente, método, rota, corpo vazio e header `X-Local-Editorial: 1`. POST exige Origin igual à UI. OPTIONS, origens externas, Host diferente, body, query e percent-encoding são recusados. Só após essa validação o proxy remove Origin e o header da UI; cookies e Authorization também não são encaminhados. A API mantém sua rejeição a todo Origin e não ganha CORS. Ambos os servidores usam apenas loopback. Não existe autenticação entre processos/usuários locais: o diretório e a máquina devem ser controlados pelo operador.

## Catálogo e histórico

HTTP **1.1.0**, extensão aditiva do protocolo 1.0.0. Serviço 1.0.0, seletor 2.0.0, claims v5, renderer 5.0.2 e artefato 3 permanecem iguais.

- `GET /api/v1/local-analysis/`: metadados dos contextos carregados; não retorna evidências, prompts ou caminhos locais. Datas opcionais válidas vêm do arquivo de origem. `asOfDate` é o corte **informado pela origem**, não reconstrução point-in-time nem um novo filtro aplicado pelo motor. Ausência/invalidade aparece como “não informado”. Esses metadados não alteram a identidade canônica do motor.
- `GET /api/v1/local-analysis/{gameId}/attempts`: tentativas concluídas, verificadas pelos mesmos hashes usados na recuperação, ordenadas por início decrescente. Cada item tem `attemptId`, `startedAt`, `resultIdentity`, `sourceSha256`. `unavailableInStore` conta entradas incompletas, corrompidas ou inesperadas no diretório inteiro, inclusive uma geração ainda em andamento; não atribui essas entradas ao jogo selecionado.
- POST de geração e GET por UUID mantêm o contrato anterior.

O histórico lê o disco e verifica artefatos a cada consulta; não há paginação nesta primeira versão, destinada a pequenos lotes locais. Uma origem com bytes diferentes é identificada como “Contexto anterior”, mesmo que o contexto canônico continue equivalente. Tentativas indisponíveis não aparecem como análises válidas.

A interface não gera ao carregar, selecionar jogo ou recarregar. Uma operação em andamento desabilita ações concorrentes daquele confronto. Ao trocar de jogo, respostas antigas não entram na nova tela. Falhas de rede não repetem POST automaticamente: consultar o histórico antes de tentar novamente evita duplicação de uma geração cuja resposta se perdeu. Os textos são renderizados como texto escapado, com quebras de linha preservadas.

## Verificar

```bash
npm --prefix web-ui test
npm --prefix web-ui run lint
npm --prefix web-ui run build
```

Com os dois servidores em execução e um nome novo de saída:

```bash
python3 scripts/verify_local_editorial_ui.py \
  editorial/local-interface-v1/runtime/http-checks-novo.json
```

O script realiza 21 verificações HTTP em loopback e **gera duas tentativas** para o primeiro contexto do catálogo. Não sobrescreve o arquivo de evidência. Testes Java cobrem catálogo, integridade do histórico, reinício e proveniência entre versões, além da paridade dos 21 casos anteriores. Testes frontend verificam limites do proxy, envelopes, isolamento de jogo, recuperação, erros e escape de texto.

Evidências da implementação: [relatório](../editorial/local-interface-v1/REPORT.md). Resultados e capturas em `runtime/` são arquivos locais ignorados; sua ausência num checkout novo não impede a reprodução do fluxo.

## Leitura visual E2/E3 integrada localmente

A branch de integração `codex/visual-integration-e2-e3` incorpora E2 e E3 e acrescenta leitura visual à mesma entrada de desenvolvimento. A UI consulta `GET /api/v1/local-analysis/{gameId}/{attemptId}/insights` por tentativa, após a consulta textual. Tentativas legadas v3 exibem texto e aviso de compatibilidade. Um documento inválido ou divergente da tentativa gera erro visível; não se converte silenciosamente em análise. O modo de fixtures é rotulado como sintético e separado de resultados reais.

O fluxo real catálogo → POST → GET visual → histórico → recarga e o reinício da API foram verificados em 07/10/2026. O visual precede o texto, que fica expansível. O build público continua independente. [Aceite da integração](plans/visual-v1/integration-report.md); [relatório histórico E3](plans/visual-v1/e3-report.md).

## Apresentação E4 e avaliação pendente

A branch local E4 acrescenta ataque/defesa e período à leitura rápida, navegação focável para encontros/histórico/texto e tabela rolável por teclado. A restrição principal precede os pontos; séries podem ficar lado a lado e se reorganizam com texto ampliado. Contrato, números, seleção e renderer permanecem iguais. A ampliação de texto a 200% foi inspecionada por CSS temporário em viewport fixo e restaurada; não equivale a zoom nativo do navegador ou certificação de acessibilidade. [Resultados e reprodução E4](plans/visual-v1/e4/REPORT.md); [rodada humana preparada, ainda pendente](plans/visual-v1/e4/human-round.md).


## Observações auditáveis — E5c-3 candidata

O mesmo laboratório tem um modo separado para bundles E5c-2 completos, validados
e rederivados por Python ao iniciar. Ele exibe uma observação por vez, com valores
exatos, denominadores, períodos e limites; não produz comparação ou pregame.
Configuração é exclusiva do operador, fora de `web-ui`; conteúdo fica congelado
na sessão, sem releitura por clique. Ver [operação e verificações](plans/metrics/e5c-3/README.md)
e [contrato de transporte](plans/metrics/e5c-3/TRANSPORT.md). A prova desta entrega
é sintética por orientação do orquestrador; o extrato real isolado não é aceito
como bundle. Production continua pela entrada estática independente.
