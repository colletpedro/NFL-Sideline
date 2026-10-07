# Aceite operacional E2/E3 — 07/10/2026

**E2 e E3 integradas localmente**, na branch `codex/visual-integration-e2-e3`. A próxima etapa de produto é E4: avaliar compreensão e densidade visual. Este aceite não aprova publicação, qualidade editorial independente ou as regras BASIC/FULL.

## Linhagem e escopo

Base E1 `5096a58`; fast-forward dos commits E2 `d3b0082`, `1b3bb8a`, `41d21b5`; cherry-pick de E3 `846713a` como `916e88f`. O commit E1 da frente E3 (`7b69316`) tinha árvore idêntica a `5096a58`, portanto não foi duplicado. `main` e as branches das frentes permaneceram em seus commits anteriores.

A integração ajustou quatro problemas de apresentação observados:

- Os quatro blocos textuais precediam os gráficos. Agora a leitura visual vem primeiro; texto completo e identificação permanecem expansíveis. Tentativas sem visual conservam o texto visível.
- Séries vazias exibiam “0 jogadas observadas”. Agora indicam volume não informado.
- Eixos reais exibiam decimais completos. Rótulos usam três algarismos significativos e `≈`; domínio, coordenadas e valores exatos não foram alterados. Valores muito pequenos usam notação científica sem virar zero.
- A direção de qualidade da defesa estava apenas no detalhe. A legenda explicita “menor EPA permitido é melhor”; a definição expansível também contempla o panorama geral.

Nenhuma alteração no seletor, claims, renderer textual, projetor ou contrato E1. A mensagem de ausência visual não presume mais que todo artefato v3 seja antigo: fases fora do enum visual também podem produzir v3 novo.

## Verificação integrada

[Registro estruturado](integration-verification.json).

| Verificação | Resultado |
| --- | --- |
| Java 21, `mvn -f core-api/pom.xml -o clean verify` | 127 testes, sem falhas/erros/ignorados |
| Frontend | 116 testes; 111 comuns + cinco regressões legadas com falha esperada |
| Contrato Python | 12 testes; 20 fixtures válidas e 15 inválidas rejeitadas; freeze preservado |
| Lint, build público, `git diff --check` | Passaram |
| Backend E2 → validador e componentes E3 | 17 documentos reais aceitos/renderizados nos testes frontend |
| HTTP real através do proxy Vite | 73 requisições: catálogo, 17 POSTs, GET textual/visual, histórico, v3 e limites do proxy |
| Reinício da API, mesmo armazenamento | 72 GETs; mesmos documentos, identidades e bytes; nenhuma geração no replay |
| Arquivos preservados | 44 hashes de contrato/snapshots/migrations iguais; seis arquivos da origem v3 histórica inalterados |
| Build público | Ausentes os marcadores do modo local, rota proxy, contrato visual e proveniências locais/sintéticas |

No navegador integrado, BAL–DAL foi gerado por clique e recuperado pelo histórico após recarga; o texto completo abriu e fechou por teclado. A tentativa v3 histórica retornou texto e aviso de incompatibilidade visual. CHI–BAL mostrou cobertura desigual com documento real. O modo sintético permaneceu separado e rotulado.

Foram inspecionadas larguras de 1440, 390 e 320 px; não houve transbordamento horizontal da página. A tabela tem rolagem interna em telas estreitas. O foco de teclado permaneceu visível. As capturas foram inspecionadas durante a sessão; não foram adicionadas novas imagens ao repositório. **Zoom de texto a 200% não foi testado nesta integração**; permanece no checklist de acessibilidade de E4. As dimensões temporárias do navegador foram restauradas.

As respostas completas, tentativas e logs desta execução ficam somente em `/tmp/nfl-visual-integration-20261007`; seus hashes no registro estruturado documentam a execução, sem prometer disponibilidade desses arquivos em outro checkout. O script abaixo reproduz os fluxos com novos UUIDs e horários, preservando as identidades determinísticas.

## Reproduzir sem `.env`

Execute a partir da raiz, com Java 21 e dependências locais disponíveis. Use um diretório novo; os comandos não instalam dependências nem acessam serviços externos.

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
mvn -f core-api/pom.xml -o clean verify
npm --prefix web-ui test
npm --prefix web-ui run lint
npm --prefix web-ui run build
python3 scripts/verify_visual_contract.py
python3 scripts/test_visual_contract.py

python3 - <<'PY'
import json, shutil
from pathlib import Path
run = Path('/tmp/nfl-visual-integration-new')
run.mkdir()
(run / 'contexts').mkdir()
(run / 'results').mkdir()
manifest = json.loads(Path('editorial/evaluations/2026-10-06-visual-e2/manifest.json').read_text())
for item in manifest['documents']:
    shutil.copy2(item['sourceContext'], run / 'contexts' / (item['gameId'] + '.json'))
PY
```

Em um terminal, mantenha a API em execução:

```bash
env -i PATH=/usr/bin:/bin LANG=en_US.UTF-8 \
  "$JAVA_HOME/bin/java" -jar core-api/target/core-api-0.1.0.jar \
  editorial-local-serve /tmp/nfl-visual-integration-new/contexts \
  /tmp/nfl-visual-integration-new/results 18081
```

Em outro, execute `npm --prefix web-ui run editorial:dev`. Abra `http://127.0.0.1:18083/`, escolha um contexto, gere uma tentativa, recarregue e recupere-a pelo histórico.

```bash
python3 scripts/verify_visual_integration.py \
  /tmp/nfl-visual-integration-new/results /tmp/nfl-visual-integration-new/http.json
```

Encerre somente a API com Ctrl-C, inicie-a novamente com os mesmos argumentos e execute:

```bash
python3 scripts/verify_visual_integration.py \
  /tmp/nfl-visual-integration-new/results /tmp/nfl-visual-integration-new/restart.json \
  --replay /tmp/nfl-visual-integration-new/http.json
```

O script também verifica tentativas v3 íntegras se existirem no diretório. O checkout não inclui a tentativa operacional histórica usada nesta sessão; reproduzir esse caso real exige uma cópia local dela. O teste Java `LocalVisualStoreTest` cobre o leitor v3 deterministicamente sem esse arquivo histórico. Bind local pode exigir permissão do ambiente. Encerre ambos os servidores com Ctrl-C ao finalizar.

## Limites e próximo passo

- `REG`/`POST` continuam no contrato visual v1. `WC`/`DIV`/`CON`/`SB` preservam texto em v3 e retornam 409 na consulta visual. Não ampliar ou traduzir silenciosamente o enum; a revisão precisa ser coordenada por versão.
- Os 17 contextos são regressões conhecidas. Os antigos reservados já foram abertos; não são novos holdouts.
- As cinco regressões legadas de sinal/tempo do painel público permanecem abertas. A leitura visual local não as corrige.
- E4 deve medir se é possível reconhecer ataque/defesa, sinal, período, lacunas e limites sem abrir tabelas; observar repetição, quantidade de texto, acesso ao histórico e detalhes. Só depois decidir ajustes de apresentação ou necessidade de dados mais ricos.
- Histórico continua uma lista recuperável, sem comparação semântica de duas tentativas. BASIC/FULL, novas métricas, integração pública e publicação ficam para entregas próprias.

Não houve push, deploy, banco remoto, modelos externos, mudança no manifesto de aprovações ou snapshots públicos. Os 36 arquivos históricos não rastreados foram preservados fora do commit.
