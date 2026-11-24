# Resultado do lote autorizado — 27/09/2026

**Avaliação editorial bloqueada por falha do provedor.** Foram consumidas 6 das 10 tentativas autorizadas. Nenhuma retornou resposta de análise. O último erro foi HTTP 402; a causa específica no provedor não foi confirmada. Não foram gerados textos novos, atribuídas notas editoriais, ajustados prompts por qualidade ou abertos os casos reservados.

## Tentativas e orçamento

| Fase | Caso | Resultado |
|---|---|---|
| Inicial, 1 | ARI–SF | Falha UNKNOWN; status não preservado pelo cliente anterior |
| Inicial, 2 | BAL–DAL | Falha UNKNOWN; status não preservado pelo cliente anterior |
| Inicial, 3 | NE–JAX | Falha UNKNOWN; status não preservado pelo cliente anterior |
| Inicial, 4 | CHI–BAL | Falha UNKNOWN; status não preservado pelo cliente anterior |
| Reavaliação, 5 | ARI–SF | Falha UNKNOWN; classe `HttpClientErrorException`, sem status preservado |
| Reavaliação, 6 | BAL–DAL | `HTTP_4XX`, **HTTP 402**, classe `HttpClientErrorException` |
| Reavaliação | NE–JAX, CHI–BAL | Não enviados após interrupção por erro HTTP |
| Reservados | SEA–WAS, MIN–TB | Não enviados; desenvolvimento não avaliado e ajustes editoriais não congelados |

Restam 4 tentativas dentro da distribuição autorizada: 2 de desenvolvimento e 2 reservadas. Não há novas chamadas agendadas ou execução automática. As 4 falhas de transporte anteriores à autorização continuam em `baseline-development/`, separadas das 6 tentativas desta autorização. Elas não foram apagadas nem tratadas como respostas bem-sucedidas.

Os arquivos `authorization.json`, `reservation-*.json`, `completion-*.json` e `attempt-ledger.json` registram autorização, reservas e consumo real. Reservar 4 vagas não significa realizar 4 chamadas; a continuação de desenvolvimento parou após uma chamada. Não atribuímos retroativamente HTTP 402 às primeiras cinco falhas, pois seus status foram perdidos pelo código anterior.

## Diagnóstico e ajustes locais

DNS e HTTPS foram verificados com HEAD público e um POST de texto fictício na raiz do serviço, sem chave e sem rota de geração. Esses testes não chamaram o modelo nem enviaram contextos. O diagnóstico seguinte mostrou erro HTTP do cliente; o código anterior convertia status fora de uma pequena lista em UNKNOWN e descartava seu número.

O cliente agora preserva apenas categoria, status HTTP e nomes de classes de exceção, sem mensagens remotas, corpo de erro, credenciais ou encadeamento de causas. O avaliador registra cada tentativa antes do envio e interrompe o lote na primeira falha de geração. A continuação só visita diretórios ainda inexistentes; não repete casos já tentados nem sobrescreve artefatos.

Na sexta tentativa foi testado envio com tamanho explícito do corpo JSON. A resposta HTTP 402 não sustentou a hipótese de falha de transferência; essa alteração experimental foi retirada do código final. A versão efetivamente usada nessa tentativa está preservada em `provenance/adjusted-remainder/`. O prompt, schema, modelo e renderer editoriais permaneceram iguais aos da rodada inicial. Não há melhoria editorial demonstrada.

## Artefatos e integridade

- `authorized-initial/`: quatro tentativas, com contexto, prompt de usuário, configuração/versão da execução, início da tentativa e falha categorizada.
- `authorized-adjusted/`: duas tentativas; `run.json` e `resume-*.json` preservam as duas invocações. Não houve repetição automática.
- `provenance/initial/`, `adjusted/`, `adjusted-remainder/` e `final/`: cópias locais e hashes das versões relevantes. Arquivos de código não foram enviados ao modelo.
- `evaluation-results.json`: avaliação marcada como indisponível por ausência de resposta, com notas nulas. Não há claims, rejeições de claims ou textos renderizados a inventar; as falhas ocorreram antes dessa etapa.
- `regression/originals.json`: caches 56–71 com contexto efetivamente armazenado em 22/09/2026; 16/16 hashes e textos conferiram com o manifesto/snapshot. Não foram atualizados com dados posteriores nem enviados ao Gemini.
- `verification.json`: resultado do gate Java, hashes de publicação e confirmação de que os seis contextos, prompt e renderer não mudaram durante a avaliação.

## O que continua sem resposta

A relevância da tese, a utilidade do contraponto, a clareza e a repetição dos novos textos **não puderam ser avaliadas**. Os 16 originais continuam úteis para regressão de integridade e corte temporal, mas não substituem respostas reais do novo contrato. CHI–BAL continua sendo somente um cenário retrospectivo com semanas desencontradas; não há reconstrução da disponibilidade da ingestão em 2025.

Os problemas já identificados nos textos legados de desenvolvimento permanecem: ARI–SF privilegia um extremo semanal e conclui exploração; o alerta de BAL–DAL reforça a tese em vez de contrapô-la; NE–JAX mistura semanas e usa qualificações permanentes com amostra curta. Não se demonstrou que o novo fluxo os corrige em respostas reais.

Antes de retomar geração, falta esclarecer/resolver o HTTP 402 na conta ou no acesso ao provedor. O status isolado não permite afirmar qual configuração de cobrança/acesso está errada. Não recomendamos ampliar o lote, trocar o modelo ou publicar textos com base nesta execução.

Nenhum banco, seleção editorial, snapshot ou deploy foi alterado. A correção da interface também não foi publicada nesta etapa.

## Diagnóstico técnico com a chave PROD — 27/09/2026

O usuário autorizou uma chamada adicional de diagnóstico, debitada do saldo de desenvolvimento. O script `diagnose_prod_key.py` verificou o controle em 6/10, registrou a tentativa 7/10 antes do envio e fez **uma** chamada ao endpoint oficial de `gemini-3.1-pro-preview`, com o único texto `Responda apenas OK.`. `credentialSource` foi `GEMINI_API_KEY_PROD`; não houve fallback para a outra chave. Redirecionamentos e retries foram desativados. Nenhum contexto, prompt editorial, cache ou arquivo do repositório foi incluído na requisição.

Resultado: **rejeição HTTP 402**, `error.code=402`, `error.status=RESOURCE_EXHAUSTED`. A chamada não produziu texto nem `finishReason`. O status estruturado aponta para exaustão de recurso/cota; o detalhe disponível não permite confirmar saldo zerado, configuração de cobrança específica, credencial inválida ou falta de permissão. Este resultado pertence apenas à chave PROD e não explica retroativamente as seis tentativas anteriores. O corpo bruto do erro e a chave não foram registrados.

O controle está em **7/10 tentativas consumidas**: **1 tentativa de desenvolvimento** e **2 reservadas** permanecem. O diagnóstico não conta como avaliação editorial e os casos reservados continuam fechados. A próxima ação é verificar no provedor o acesso, as cotas e a cobrança associados à chave PROD antes de decidir sobre qualquer outra chamada. Nenhuma outra chamada foi feita nesta etapa.

## Comparação das duas credenciais — 29/09/2026

A pedido do usuário, foram feitas exatamente duas chamadas independentes ao modelo `gemini-3.1-pro-preview`, cada uma com apenas `Responda apenas OK.`: tentativa 8 usando `GEMINI_API_KEY` e tentativa 9 usando `GEMINI_API_KEY_PROD`. As duas retornaram **HTTP 402**, `error.code=402`, `error.status=RESOURCE_EXHAUSTED`, sem texto nem `finishReason`. Não houve retry. Os diagnósticos individuais e a comparação sanitizada estão em `credential-diagnostic-both/`.

O resultado é igual nas duas chaves e indica exaustão de recurso/cota. Continua indeterminado se a razão é cobrança, saldo, cota, projeto ou outro limite; não confirma saldo zerado nem invalidez de credenciais. Também não prova que as chaves compartilham projeto. Os diagnósticos antigos da tentativa 7 e das tentativas 1–6 não foram reinterpretados.

O total é **9/10**: desenvolvimento 0 restante e 1 tentativa reservada restante. Um dos dois espaços antes reservados foi usado somente para este diagnóstico técnico; **nenhum holdout editorial foi aberto**. Próxima ação: verificar configuração de cota, acesso e faturamento no provedor para cada chave/projeto antes de nova geração. Nenhuma outra chamada foi feita.
