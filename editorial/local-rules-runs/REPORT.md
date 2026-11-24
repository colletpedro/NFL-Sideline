# Entrega do motor editorial local 1.0.0

Implementação concluída e validada offline. Não houve geração externa, banco remoto, instalação de
modelo, escrita em análises aprovadas/snapshots/frontend, commit, push ou deploy. As alterações que já
existiam no workspace foram preservadas. Os artefatos deste diretório não constituem publicação.

## Implementação e decisões

- Interface tipada `ClaimSelector`, resultado `ClaimSelection` e parâmetros editoriais independentes de
  provedor. Seletor determinístico `LocalRuleSelector`; `ClaimValidator` separado de `ClaimRenderer`.
- Claims v4 neutras, com OPPORTUNITY e vínculos explícitos DIRECT_CONFLICT / INDEPENDENT_OPPORTUNITY;
  v3 e os consumidores Gemini anteriores preservados. Quatro campos públicos inalterados.
- Seis confrontos enumerados; preferência categórica por cobertura atual/recente/comparável e depois
  fundamentos específicos. Empates preservados integralmente; magnitude do EPA não desempata.
- Semanas/volumes/variação preservados. Oportunidade exige sinais estritamente positivos em cada semana
  dos dois recortes adequados. A cobertura conservadora exige as até três semanas numéricas imediatamente
  anteriores: lacunas não viram dados nem presumem bye. Suficiência estatística não é afirmada.
- Todas as oportunidades elegíveis permanecem no veredito, inclusive de fundamentos correlacionados,
  sem contar votos. Todos os resultados são INCONCLUSIVE com thesis_team NONE.
- Auditoria persistente com hashes de entrada e contexto normalizado, identidade/versões, candidatos,
  motivos, referências, textos e diagnósticos sanitizados. Cada execução exige diretório novo.

Política completa e divergências observadas: [documentação](../../docs/local-rules-editorial.md).
A descrição de `metricas_citadas` no AGENTS.md não corresponde ao caminho atual de claims v3 já existente;
Spec.md tinha cabeçalho v2 divergente do código/seção 7. Essas diferenças foram registradas, sem alterar
AGENTS.md ou reinterpretar o status da avaliação Gemini.

## Reprodução

Da raiz do repositório, com o JDK 21 disponível nesta máquina:

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
mvn -f core-api/pom.xml -o clean verify
mkdir -p editorial/local-rules-runs
java -jar core-api/target/core-api-0.1.0.jar editorial-local \
  editorial/evaluations/2026-09-26/contexts/2026_03_BAL_DAL.json \
  editorial/local-rules-runs/exemplo-bal-dal
```

Não carregar `.env`. O destino deve ser novo. O comando recusa sobrescrita, inclusive de tentativa
rejeitada. Consultar também `scripts/evaluate_local_rules.py` para execução por split e congelamento.
O JAR está incluído nos hashes: uma recompilação pode mudar seu hash de empacotamento e exige um novo
selo para uma avaliação futura; não se deve reinterpretar o selo desta entrega como válido para outro JAR.

## Validação e avaliação separada

`mvn -f core-api/pom.xml -o clean verify` executado com **Java 21.0.12.1**: **95 testes, zero falhas,
zero erros, zero ignorados**. Log: [java21-clean-verify.log](java21-clean-verify.log).
`git diff --check` passou; verificação adicional de whitespace incluiu arquivos novos não rastreados.
[Verificação estruturada](verification.json).

Foram acrescentados 14 testes (11 de seleção/contrato e 3 de execução/auditoria). Um teste percorre
180 contextos sintéticos determinísticos e suas remoções/trocas de times. Há verificações de invariância
por reordenação, duplicação, mercado e mando; simetria por troca de times; abstenção; restrições de contrato;
fontes ausentes/parciais/históricas; sinais próximos de zero/mistos; outlier semanal; semanas/denominadores
incompatíveis; empates; oportunidades dos dois lados; não sobrescrita e rejeição de caminhos públicos.
Os testes preexistentes de claims v3, serviço/cache e restante do backend também passaram.

Os quatro casos de desenvolvimento foram executados antes do congelamento. `development-v1` conserva
uma execução anterior do desenvolvimento, antes de compactar alertas com múltiplos encontros e melhorar
um código de motivo; a referência final é **development-final**. Nada foi sobrescrito.

O selo [rules-v1.freeze.json](rules-v1.freeze.json) foi criado em **2026-10-01T01:56:29.085123+00:00** antes da primeira leitura
dos contextos reservados por este motor. Os dois IDs foram identificados previamente apenas pelo
manifesto. O comando holdout conferiu os hashes de fontes, testes, documentação, script, manifesto e JAR
antes da leitura. Uma nova conferência após a execução confirmou todos os arquivos congelados intactos.
Não houve ajuste baseado nos reservados. Nenhum resultado Gemini reservado foi consultado.

| Caso | Split | Resultado local |
|---|---|---|
| ARI–SF | Desenvolvimento | Conflitos nos seis encontros; quatro alternativas específicas preservadas. |
| BAL–DAL | Desenvolvimento | Passe e corrida de BAL empatados como principais; panorama de BAL também preservado no veredito. |
| NE–JAX | Desenvolvimento | Conflitos nos seis encontros; nenhuma oportunidade elegível. |
| CHI–BAL (2025) | Desenvolvimento | Semanas diferentes e lacunas; panorama geral descritivo, sem oportunidade. |
| SEA–WAS | Reservado | Oportunidade no passe de SEA; panorama de SEA preservado no veredito; limitação de duas semanas. |
| MIN–TB | Reservado | Quatro encontros conflitantes e dois perfis; nenhuma oportunidade; múltiplos fundamentos específicos. |

**6/6 análises passaram pelo validador**, todas inconclusivas e sem time escolhido.
[Resumo estruturado](evaluation-summary.json), [resultados de desenvolvimento](development-final/results.json),
[resultados reservados](holdout-v1/results.json). Cada subdiretório contém contexto, seleção, claims,
rendered e resultado com hashes/versões. Isso é consistência mecânica, **não qualidade editorial comprovada**.
A avaliação pendente do Gemini permanece separada e nenhuma de suas tentativas foi consumida.

## Exemplos efetivamente gerados

### SEA–WAS, reservado

[Documento completo](holdout-v1/2026_03_SEA_WAS/rendered.json),
[claims e evidências](holdout-v1/2026_03_SEA_WAS/claims.json).

**fator_chave**

> Passe de SEA contra a defesa de WAS: oportunidade condicional nos sinais observados.

**vantagem_tatica**

> SEA: EPA ofensivo por passe de +0,382 EPA (média das médias semanais, sem ponderação por jogadas; temporada atual, semanas 1, 2; 2 observações semanais; faixa +0,168 EPA a +0,596 EPA). WAS: EPA permitido por passe de +0,252 EPA (média das médias semanais, sem ponderação por jogadas; temporada atual, semanas 1, 2; 2 observações semanais; faixa +0,045 EPA a +0,458 EPA). O ataque produziu EPA positivo e a defesa adversária permitiu EPA positivo em cada semana observada nesse fundamento. É uma oportunidade condicional para SEA, sem demonstrar superioridade geral ou prever exploração no jogo. Nenhuma oportunidade localizada permite escolher o vencedor do jogo.

**alerta_vermelho**

> Limitação: Ao menos um time tem no máximo duas semanas com métricas atuais; a amostra curta limita a leitura.

**veredito**

> O confronto permanece inconclusivo; nenhum time é escolhido. Ao menos um time tem no máximo duas semanas com métricas atuais; a amostra curta limita a leitura. Passe de SEA contra a defesa de WAS: oportunidade condicional nos sinais observados. Panorama por jogada de SEA contra a defesa de WAS: oportunidade condicional nos sinais observados. Os fundamentos podem ser correlacionados e não contam como votos independentes.

### BAL–DAL, alternativas empatadas

[Documento completo](development-final/2026_03_BAL_DAL/rendered.json).

> Há múltiplos recortes para descrever, sem eleger um fundamento único. Passe de BAL contra a defesa de DAL: oportunidade condicional nos sinais observados. Corrida de BAL contra a defesa de DAL: oportunidade condicional nos sinais observados.

### CHI–BAL, limitação de cobertura

[Documento completo](development-final/2025_08_CHI_BAL/rendered.json).

> O confronto permanece inconclusivo; nenhum time é escolhido. Os times têm semanas observadas diferentes; não há ajuste por adversário nesses recortes. Panorama por jogada de CHI contra a defesa de BAL: sinais positivos e negativos coexistem no encontro, sem direção sustentada. Os fundamentos podem ser correlacionados e não contam como votos independentes.

## Limitações que permanecem

- Cobertura de semanas numéricas é conservadora: pode se abster em byes e atrasos reais. Não há calendário
  de disponibilidade/denominadores específicos que resolva essas lacunas.
- Conflito positivo/negativo é amplo: pode ocorrer em uma janela ou entre ataque e defesa. Não mede
  magnitude prática, força ou causalidade. Valores muito pequenos podem arredondar a zero no texto.
- O contraponto direto desta versão se limita à contradição nos próprios recortes principais. Não busca
  mecanismo causal, lesões, tracking ou outras métricas como refutação. Uma oportunidade independente
  do adversário não é apresentada como prova contrária direta.
- Resumos de empates repetem classificações e omitem os detalhes numéricos do texto público, preservados
  internamente. Isso evita um desempate artificial, mas a concisão/relevância para o leitor precisa de avaliação.
- O veredito repete oportunidades do panorama geral junto aos fundamentos específicos, com ressalva
  explícita de correlação. Não significa suporte adicional nem três votos para um time.
- Apenas seis contextos congelados e fixtures sintéticas; não há backtest, calibração, ajuste por adversário,
  shrinkage ou comprovação de qualidade editorial. Os reservados não motivaram ajustes nesta entrega.

Os snapshots públicos não têm diff contra o git e seus hashes permaneceram iguais durante o holdout.
O manifesto de análises aprovadas não foi alterado. As modificações anteriores do frontend continuam
no workspace e não foram feitas por esta entrega.
