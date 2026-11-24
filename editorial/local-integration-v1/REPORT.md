# Integração local restrita — entrega

Implementação concluída e validada mecanicamente. A tentativa de HTTP real foi bloqueada
pelo sandbox; não se afirma que houve requisição HTTP real bem-sucedida. Não há promoção
editorial, publicação ou avaliação independente.

## Arquitetura e versões

`LocalGenerationService` 1.0.0 recebe contexto, parâmetros e ClaimSelector. Seleciona,
valida pelo ClaimValidator comum e só então renderiza; retorna textos tipados, seleção
completa e identidade. A CLI anterior usa essa orquestração e conserva os argumentos,
códigos de saída e proteções de escrita. Artefato interno passa de 2 para **3**, com
identidade estruturada **local-result-1** e parâmetros explícitos.

`LocalAnalysisServer` inicia HttpServer JDK somente pelo comando `editorial-local-serve`,
em 127.0.0.1. Não cria aplicação Spring. Catálogo validado na inicialização congela os
contextos locais em memória; nenhuma requisição escolhe arquivos. `LocalResultStore`
reserva UUIDs, mantém tentativas distintas e disponibiliza resultados completos por
marcador atômico com hashes. Lock exclusivo impede dois donos do mesmo armazenamento.

**Inalterados:** seletor local-descriptive-rules 2.0.0, entrada v3, claims v5, renderer
controlled-claims-v5.0.1, seleção, sinais, cobertura, agregações, recortes e redação.
NONE/INCONCLUSIVE e os quatro campos públicos continuam iguais. Nenhum adaptador fictício,
fallback ou seleção automática de provedor. Gemini continua em seu fluxo anterior.

## Baseline e identidade nova

Antes de qualquer alteração de fonte ou rebuild, o check do congelamento histórico
conferiu **138/138 arquivos**, sem divergências. Todos foram copiados, inclusive JAR,
fontes, fixtures, documentos e harness, para [baseline](baseline/).

- [Linhagem e hashes originais](baseline-lineage.json).
- [Verificação das cópias e reprodução](baseline-verification.json).
- [Resultado executado com o JAR antigo](baseline-reproduction/result.json).
- [Hashes da implementação nova](implementation-identity.json).

O JAR arquivado tem SHA-256
`30c4880142f393d5314022ad5bb5ee43495757957388b1a7f805d053af2dda1c`.
O JAR final desta entrega tem SHA-256
`e742e8040b838356aac90a0fdbb1b0fd54df3b3ea9b763625a892bd95e6b0f7b`.
O congelamento histórico está intacto. Fontes alterados e JAR novo **não correspondem**
aos hashes históricos; um check histórico contra a árvore atual deve detectar isso.

Reprodução do JAR preservado, da raiz, com destino ainda inexistente:

```bash
/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home/bin/java \
  -jar editorial/local-integration-v1/baseline/core-api/target/core-api-0.1.0.jar \
  editorial-local \
  editorial/local-integration-v1/operational/contexts/2026_03_BAL_DAL.json \
  editorial/local-integration-v1/baseline-reproduction-02
```

## Testes desta entrega

[Gate final Java 21](java21-clean-verify-final.log): **115 testes, 0 falhas, 0 erros,
0 skips**. Comando executado da raiz (a propriedade adicional apenas salva evidência do
teste do handler; o diretório de evidência deve ser novo):

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
mvn -f core-api/pom.xml -o clean verify \
  -Dlocal.integration.evidence="$PWD/editorial/local-integration-v1/handler-validation-02"
git diff --check
```

O gate sem essa propriedade também foi executado nesta entrega e passou; veja
[java21-clean-verify.log](java21-clean-verify.log). O gate final corresponde às fontes
finais, incluindo a gravação opcional da evidência do handler.

Cobertura acrescentada: paridade CLI/serviço e baseline nos **21 casos expostos**;
igualdade dos quatro textos, documento completo, referências, candidatos, decisões e
versões; rejeição comum de claims inválidas; 12 gerações concorrentes com uma identidade
e 12 tentativas distintas; consulta após reinício; exclusão de segundo dono; corrupção,
tentativa interrompida, falha sem marcador válido; separação de identidade por seletor,
versão, contrato, renderer e parâmetros; catálogo ambíguo, ID inválido, symlink e traversal.

O teste de inicialização usa classloader que proíbe carregar Spring, Hikari, Hibernate,
JPA, repositórios, GeminiClient e exportador: inicialização e start passam com transporte
simulado. Isso verifica isolamento de construção, não apenas ausência de chamadas aos
clientes. Scanner confirma nenhuma classe local como componente; MockMvc dos controllers
normais retorna 404 nas rotas locais. Os testes anteriores de Gemini, snapshot e contratos
v3/v4 também passaram, sem chamadas reais ao Gemini.

Os testes do handler executam POST/GET com HttpExchange simulado e os componentes reais
de catálogo, serviço e armazenamento. O socket é substituído explicitamente no teste.
Isso **não** é HTTP de rede.

## Validação operacional e exemplo executado

Tentativa real: comando `editorial-local-serve ... 18081` em ambiente mínimo, sem
credenciais. O servidor encerrou com `SocketException`; uma sondagem em 127.0.0.1 com
porta dinâmica confirmou `PermissionError: Operation not permitted`. Nenhuma escalada
ou alternativa para contornar a restrição foi utilizada. O processo iniciado está encerrado.

- [Comando, resultado e encerramento](operational/validation.json).
- [Log do servidor](operational/server.log).
- [Diagnóstico do bloqueio de bind](operational/bind-diagnostic.json).

Consequentemente, **não existe exemplo de requisição/resposta real via rede nesta entrega**.
O exemplo abaixo foi de fato executado no handler em teste, com status 201 e consulta 200:

```text
POST /api/v1/local-analysis/2026_03_BAL_DAL
GET /api/v1/local-analysis/2026_03_BAL_DAL/fb489533-3e14-4e04-9257-a523aacb932f
```

Identidade retornada:
`690681b6c05e34a57797fcc25027ba80afc35cf8e85d3dcef0a26c1e10d70164`.
Trecho exato do fator-chave: “Passe e Corrida de BAL contra DAL: sinais compatíveis com
uma oportunidade localizada.” A resposta traz `mode: LOCAL_RULES_DEVELOPMENT`,
`publicationApproved: false` e os quatro textos dentro de `analysis`.

[POST completo](handler-validation/post-response.json),
[GET completo](handler-validation/get-response.json) e
[identificação explícita do transporte simulado](handler-validation/transport.json).

O JAR final também gerou BAL–DAL pela CLI:
[metadados](new-cli-validation/result.json), [quatro textos](new-cli-validation/rendered.json),
[claims](new-cli-validation/claims.json), [auditoria](new-cli-validation/selection.json).
Claims, seleção e textos coincidem com o JAR arquivado; os quatro textos coincidem com a
resposta do handler. Esses artefatos não se passam por análises aprovadas.

[Guia operacional](../../docs/local-editorial-api.md) contém comandos exatos para iniciar,
curl de geração/consulta, encerramento, formato das respostas, diretórios, identidade,
concorrência e tratamento de falhas. A execução HTTP completa ainda precisa de um ambiente
que permita bind local, usando esses comandos sem alterar a implementação.

## Integridade e escopo

[Verificação desta entrega](integrity-verification.json): 692 arquivos anteriores
comparados; **689 intactos**. Só três arquivos preexistentes mudaram nesta entrega:
Spec.md (complemento), CoreApiApplication.java (dispatch explícito) e
LocalAnalysisApplication.java (uso do serviço). As mudanças anteriores do usuário nesses
arquivos foram preservadas. Os demais componentes desta entrega são arquivos novos.
`git diff --check` passou. Fontes das regras/renderer e arquivos de frontend, snapshots,
análises aprovadas, manifestos de publicação, avaliações Gemini e lotes anteriores ficaram
intactos em relação ao início desta sessão.

Sem geração externa, acesso remoto ao banco, download de dados, instalação/execução de
modelos, leitura de .env, migração, alteração de dados públicos, publicação, deploy, push
ou commit. Não foram alteradas versões de política editorial nem exigida revisão humana.

## Limitações e pendências separadas

A API é local e não autentica usuários do mesmo computador; os diretórios pressupõem
controle do operador. Não há índice de último resultado, cleanup, recuperação automática
ou retomada de tentativa; falta de espaço pode impedir até o diagnóstico de falha.
Hashes detectam corrupção, não adulteração coordenada por quem controla o armazenamento.
O catálogo é fixo por processo; novos contextos exigem reinício. HTTP real ficou bloqueado.

Pendências editoriais preservadas, sem correção nesta entrega: composição de faixas com
desigualdade (LV–NO), repetição de nomes/avisos, alertas extensos e inspeção visual pendente
do lote anterior. Os casos existentes não são avaliação independente. Aprovação mecânica
não demonstra qualidade editorial, capacidade preditiva ou generalização.
