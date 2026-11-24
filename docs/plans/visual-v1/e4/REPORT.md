# E4 — compreensão, propriedades visuais e apresentação

07/10/2026 · branch local `codex/visual-analysis-e4` · base exata `793ac7b0059b77c22a41236aeb77427140c87108` da integração E2/E3. Implementação: `0c42b820644e38847164435a5dc7a6c6af079e8a`.

**Apresentação ajustada e auditoria interna concluída; compreensão humana pendente.** Não houve participantes, respostas humanas ou tempos de leitura. A hipótese de localizar achado e limitação em 10–15 segundos continua sem validação. Não se declara generalização, previsão, qualidade editorial independente ou aprovação para publicação.

## Protocolo e proveniência

O [protocolo](protocol.md) e a [matriz](protocol.json) foram commitados em `35cd8dc`, antes de editar a interface. O [diagnóstico inicial](initial-diagnosis.md) foi commitado em `c098144`, após usar o navegador e antes dos ajustes. [Registro estruturado final](results.json).

Foram percorridas as 20 fixtures E1 no browser, e comparados visual e texto completo em BAL–DAL, CHI–BAL e NE–JAX. Os 17 documentos E2 continuam como regressões frontend e HTTP. Todos já eram conhecidos. Os antigos reservados já foram vistos; não foram rebatizados como holdouts.

O [inventário adicional](context-inventory.json) pesquisou contextos v3 em `editorial`, testes Java e testes ETL. O censo histórico já classificava 21 contextos únicos, 17 regressões e quatro sintéticos; cópias posteriores e fixtures não comprovam não uso no ajuste. A busca das pastas de contextos da checkout original encontrou as mesmas linhagens históricas. Uma [busca complementar incluindo arquivos ignorados](supplemental-discovery.json), feita após a implementação sem novo ajuste, examinou 945 JSONs na checkout original (`editorial`, `etl-pipeline/data`, recursos Java), encontrou 196 cópias de contexto e as mesmas 21 identidades conhecidas. O inventário completo permanece local, com hash registrado. Não foi encontrado um contexto local com proveniência suficiente para uma amostra independente. Isso limita a avaliação, sem impedir a auditoria e correções.

Uma tentativa v3 real usada na integração estava disponível em `/tmp/nfl-visual-integration-20261007`. Foi copiada integralmente para o armazenamento E4 e recuperada no browser. Os seis arquivos da origem e da cópia mantiveram seus hashes. Essa disponibilidade substituiu a construção de um caso WC sintético prevista como alternativa no protocolo; o teste Java existente cobre WC, mas WC **não** foi inspecionado no browser nesta E4. O v3 histórico também é regressão conhecida.

## Problemas observados e ajustes implementados

| Observação anterior | Ajuste E4 | Reavaliação |
| --- | --- | --- |
| Leitura rápida omitia defesa adversária e período observado | Ataque × defesa, fundamento e período na leitura rápida; mesma janela escrita uma vez, janelas diferentes separadas | BAL–DAL informa 2026/1–2; CHI–BAL preserva CHI 4/6/7 e BAL 4/5/6 |
| Restrição principal vinha depois de duas séries | Restrição junto ao achado, antes dos pontos | Principal limitação acessível antes de percorrer o gráfico |
| Papéis de ataque/defesa em 10 px | Rótulos de 14 px; textos auxiliares de pelo menos 12 px, em unidades relativas | Tamanhos computados e ampliação verificados |
| Séries empilhadas e metadados repetidos | Comparação lado a lado quando há espaço; reflow com texto ampliado; retirada da contagem redundante e do ano repetido em cada ponto | Período e volume continuam explícitos; números e recortes não mudaram |
| Destaque GENERAL levava a panorama recolhido | Botão “Ver encontro e evidências” abre o panorama e foca o cartão | CHI–BAL aberto por Enter, com foco no encontro correto |
| Histórico após todos os gráficos | Links para histórico e leitura textual antes do visual; destinos focáveis | Link por Enter focou `attempt-history`; texto permanece opcional |
| Tabela rolável sem alvo de foco | Região nomeada pelo caption, tabindex, instrução de rolagem, headers e valores exatos em uma linha | Tab → região → seta rolou a tabela; foco visível |
| Cor/quantidade poderiam sugerir placar | Ressalva de ausência de ajuste/vencedor próxima à leitura rápida; explicação do destaque lima | Empates e oportunidades dos dois ataques preservados |
| Ampliação cortava badge e rótulo do eixo; tabela fragmentava números | Cabeçalho reflow, escala mobile em linhas, indicadores de expansão em `em`, tabela com rolagem interna | Reinspeção a 200% preservou rótulos, valores, foco e controles |

O primeiro cartão de passe de BAL–DAL, na mesma largura 1440, passou de **646,8 para 562,9 px**, cerca de 13% menor. O histórico continua abaixo da leitura; o ganho é o acesso por link, não uma afirmação de que ele passou a ficar acima dos gráficos.

A quantidade total de texto visível **não diminuiu**: CHI–BAL passou de 729 para 739 tokens separados por espaços; NE–JAX, de 647 para 661. Método: `innerText` da região visual, detalhes recolhidos, sem contar tabelas/texto completo ocultos. A leitura rápida ganhou papéis e períodos; retiramos repetições estruturais, mas preservamos textos normativos E1. Essa troca favorece disponibilidade da informação, sem provar velocidade de leitura. Repetições editoriais continuam na proposta versionada abaixo.

## Inspeção interna de compreensão

As mesmas perguntas foram feitas às duas representações: achado; ataque/defesa e fundamento; temporada/semanas; principal limitação; ausência ou semanas diferentes; motivo para não inferir vencedor. O agente inspecionou o visual e depois abriu o texto na mesma UI. Não houve contrabalanceamento, pois não houve participantes; aprendizado e conhecimento prévio do agente impedem tratar essas respostas como experimento humano.

- **BAL–DAL:** ambas as representações sustentam oportunidade localizada do ataque de BAL, em passe/corrida, contra DAL, nas semanas 1/2 de 2026; amostra curta e ausência de previsão. O texto apresenta médias/faixas; o visual mostra pontos semanais. Não tratamos as estatísticas como numericamente equivalentes.
- **CHI–BAL:** ambas preservam as janelas diferentes e a limitação de cobertura. O visual destaca panoramas gerais; o botão agora alcança esses recortes sem uma busca separada no rodapé.
- **NE–JAX:** variação semanal e quatro destaques equivalentes permanecem. Quantidade de destaques não escolhe vencedor. Texto textual e visual da tentativa têm a mesma identidade validada.
- **Fixtures conhecidas:** oportunidade, oposição, ataque não demonstrado, ambos negativos, variação, empate, duas oportunidades, parcial, ausência, histórico, cobertura desigual, lacunas, zero, pequenos sinais de ambos os lados, outlier e panorama agrupado foram examinados. A falta de série não cria zero; evidência unilateral continua visível. EPA permitido negativo pode ser favorável à defesa; não foi convertido em deficiência defensiva.

O texto completo de CHI–BAL e NE–JAX foi comparado como string antes/depois e permaneceu igual. Nos três casos, as identidades E2 e o GET real reconciliam com os artefatos congelados. Não houve alteração no seletor, claims, renderer textual, projetor, métricas, recortes ou regras estatísticas.

## Propriedades, acessibilidade e operação

Frontend: **125 testes aprovados, 120 comuns e cinco regressões públicas com falha esperada**; nove testes E4 novos. Eles verificam papéis/período/ressalva da leitura rápida, janelas distintas, referência histórica, extremo acrescentado em GENERAL recolhido governando a escala renderizada, e valores/coordenadas originais de oposição, zero, sinais pequenos, unilateralidade e outlier. Mantêm as verificações anteriores de empate, ausência, underflow e validação do envelope vinculado à tentativa.

Browser IAB: 20 estados finais × 1440/390/320 = **60 inspeções**, sem transbordamento horizontal da página. Tabelas têm rolagem interna. Sequência de Tab do skip link aos seletores, geração, links, destaques e summaries manteve contorno visível e foco na área visível. Enter abriu/recolheu texto e detalhes; o destaque geral abriu e focou o panorama. A troca de fixture/tentativa reinicia detalhes por chave, sem reutilizar expansão de outro documento.

**Texto a 200%:** aplicamos temporariamente [CSS de avaliação](text200.css) somente no laboratório desta worktree, mantendo 1440×1000 e 320×740. O root de `rem` passou de 16 para 32 px; headings com `clamp` em px foram explicitamente duplicados. Onze famílias de texto medidas dobraram em cada largura (por exemplo, papel 14→28 px, valor 13→26 px, título visual desktop 34→68 px). Isso é ampliação de texto por CSS, **não redução de viewport nem zoom nativo de página**. Badge e rótulos cortados foram corrigidos e reinspecionados. A tabela de 1088 px continuou rolável dentro de 209 px; seta moveu scrollLeft para 76,5 px. CSS temporário removido e viewport restaurado. Não é certificação WCAG nem auditoria com leitor de tela.

Contraste: 186 amostras de texto visível no cenário de oposição/tabela, cores computadas e fundo opaco mais próximo, com tratamento conservador dos extremos do gradiente. Menor razão amostrada **8,49:1**; elementos essenciais de gráfico/foco **6,21:1 ou mais**. Controles desabilitados excluídos. É uma verificação dos papéis de cor amostrados e tokens de gráfico, não uma auditoria formal de todas as combinações.

O JAR foi reconstruído com Java 21 e `mvn -o clean verify`: **127 testes, zero falhas/erros/ignorados**. Nenhum `.env` foi carregado. Fluxo HTTP real pelo Vite: 17 casos/71 requisições; após reinício, 72 GETs/verificações incluindo v3. Documentos, identidades e bytes permaneceram iguais. Browser executou catálogo → geração explícita → visual → histórico → recarga e recuperação.

Falhas controladas usaram somente `/tmp/nfl-e4-20261007` e processos próprios. API E4 parada: erro visível, resultado selecionado mantido; reinício e atualização explícita recuperaram o histórico. Um [harness de transporte](../../../../scripts/evaluate_e4_transport.py) atrasou um POST bem-sucedido por dois segundos: a resposta não entrou em NE–JAX após trocar de BAL–DAL. Esse atraso é janela operacional, **não tempo de compreensão**. Outro POST foi aceito pelo Java (201), salvo e teve a resposta descartada: o browser informou confirmação perdida, não repetiu POST e recuperou a tentativa por histórico. NE passou de duas para três tentativas; o log registra somente um POST desse caso. O harness realizou apenas dois POSTs ao todo (atraso e perda). Ao concluir, as abas próprias foram fechadas e os quatro servidores E4 encerrados com comando/diretório conferidos; as portas 18081/18083/18085/18086 deixaram de ouvir.

Lint, build, contrato Python (12 testes; 20 válidas/15 inválidas rejeitadas), freeze E1 e `git diff --check` passaram. A auditoria Rollup examinou **1874 módulos processados**, sem `local-editorial`, `features/analysis-visual` ou contrato visual; o bundle também não contém os marcadores locais. Os assets públicos mantêm os mesmos nomes/hashes nesta avaliação. **602 arquivos protegidos rastreados** — contrato, Java, migrations, snapshots e histórico editorial — iguais à base. Arquivos não rastreados e binários de outras tarefas ficaram na checkout original.

## Evidências selecionadas

- [Antes, página desktop](evidence/before-desktop.jpg): captura completa da base antes dos ajustes.
- [Depois, desktop](evidence/after-desktop.jpg): BAL–DAL, foco no primeiro cartão, limitação anterior às séries.
- [Depois, 390 px](evidence/after-390.jpg) e [320 px](evidence/after-320.jpg): fixture **sintética** `opposition`, não resultado NFL real.
- [Texto 200%, desktop](evidence/text200-desktop.jpg) e [mobile](evidence/text200-mobile.jpg): BAL–DAL real conhecido, fontes ampliadas; área visível é parte da leitura rolável.

Capturas têm scrolls/áreas visíveis diferentes; a comparação de altura usa medidas DOM no mesmo caso/largura, não proporção aparente da imagem. Hashes das capturas e evidências locais estão no registro. JARs, respostas completas, snapshots DOM, logs e builds de auditoria ficam apenas no diretório temporário; seus hashes não prometem disponibilidade em outro checkout.

## Rodada humana preparada, não executada

[Instruções e perguntas](human-round.md), [formulário vazio](human-results-template.json) e três páginas textuais congeladas em `human/`. Conteúdo copiado, escapado e identificado pelo `resultIdentity`, sem reescrita do renderer. Duas ordens alternam texto/visual entre participantes; ninguém precisa ler todas as análises. Comparação exploratória: o contêiner textual separado pode introduzir efeito de apresentação e deve ser registrado.

**Resultados humanos efetivamente coletados: nenhum.** Não preenchemos tempos, acertos, preferências ou interpretações para o usuário. Usuários com exposição prévia devem ser identificados; as páginas congeladas não se tornam uma amostra independente.

## Pendências e proposta ao orquestrador

1. Executar a rodada humana antes de declarar compreensão validada ou decidir BASIC/FULL. Registrar respostas e equívocos, especialmente defesa negativa e destaques como previsão. A hipótese de 10–15 segundos deve continuar descrita como hipótese.
2. Obter uma amostra adicional com proveniência explícita de não uso no ajuste, congelar seleção/protocolo antes de abrir os resultados e avaliá-la. Não reutilizar os antigos reservados como holdout.
3. **Proposta não implementada de copy visual 1.1.0:** em `POSITIVE_CONVERGENCE`, comparar “EPA positivo no ataque e no permitido pela defesa” com “Ataque positivo; defesa permite EPA positivo”; em `SAMPLE_LIMIT`, comparar a frase atual com “Até duas semanas observadas; padrão duradouro não estabelecido”. São exemplos mínimos para teste de vocabulário/repetição, não novas inferências. Mantêm o sinal original e a ressalva. Impacto: schema/allowlist de versão, catálogo, projetor, fixtures e validação cruzada; novos documentos/identidades visuais, suporte paralelo à versão antiga e preservação integral das tentativas. Recomenda-se um pacote coordenado `visual-analysis-1.1.0` / `visual-copy-1.1.0` / projetor correspondente, aprovado pelo orquestrador. Não editar freeze E1 nem retroescrever documentos existentes. Snapshot público v1 permanece fora dessa proposta.
4. E5 deve fechar denominadores de passe/corrida, semântica de passe/dropback, cobertura e disponibilidade temporal. Uma UI mais clara não resolve esses limites de dados. As cinco regressões públicas legadas seguem abertas; corrigir/substituir antes de publicação. Enum WC/DIV/CON/SB permanece fora do visual v1.

**Recomendação concreta:** iniciar E5 pelo contrato de métricas/recortes e executar a rodada humana curta antes de E6/E7. Não liberar BASIC/FULL ou integração pública apenas com os gates mecânicos desta E4. Não houve push, deploy, merge em main, banco remoto, ETL, modelos, mudança de snapshots ou aprovações.

## Reproduzir

Na raiz da worktree, com dependências já disponíveis. `.env` não é necessária. Nunca interromper outra tarefa para liberar uma porta; se 18081/18083 estiverem ocupadas, aguardar ou usar outra sessão isolada do laboratório.

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
mvn -f core-api/pom.xml -o clean verify
npm --prefix web-ui test
npm --prefix web-ui run lint
npm --prefix web-ui run build
python3 scripts/verify_visual_contract.py
python3 scripts/test_visual_contract.py
git diff --check

export NFL_E4_RUN=/tmp/nfl-e4-reproduction-NOVO
mkdir "$NFL_E4_RUN"
python3 - <<'PY'
import json, os, shutil
from pathlib import Path
run = Path(os.environ['NFL_E4_RUN'])
(run / 'contexts').mkdir()
(run / 'results').mkdir()
for row in json.loads(Path('editorial/evaluations/2026-10-06-visual-e2/manifest.json').read_text())['documents']:
    shutil.copy2(row['sourceContext'], run / 'contexts' / (row['gameId'] + '.json'))
PY
```

Terminal da API própria:

```bash
env -i PATH=/usr/bin:/bin LANG=en_US.UTF-8 "$JAVA_HOME/bin/java" \
  -jar core-api/target/core-api-0.1.0.jar editorial-local-serve \
  "$NFL_E4_RUN/contexts" "$NFL_E4_RUN/results" 18081
```

Outro terminal: `npm --prefix web-ui run editorial:dev`. Abrir `http://127.0.0.1:18083/`, gerar por clique, inspecionar, recarregar e abrir o histórico. Para os 17 casos:

```bash
python3 scripts/verify_visual_integration.py "$NFL_E4_RUN/results" "$NFL_E4_RUN/http.json"
# Ctrl-C somente na API própria; iniciar de novo com os mesmos argumentos.
python3 scripts/verify_visual_integration.py "$NFL_E4_RUN/results" "$NFL_E4_RUN/replay.json" \
  --replay "$NFL_E4_RUN/http.json"
```

v3 histórico não integra o checkout: copiar um armazenamento v3 íntegro conhecido se disponível, sem editar a origem. Sem essa cópia, `LocalVisualStoreTest` reproduz o mecanismo v3 e o caso WC em diretório temporário, mas isso não é uma nova observação humana ou histórica real.

Para perda/atraso: encerrar somente a API própria em 18081; iniciá-la com porta **18085** e os mesmos diretórios. Em outro terminal:

```bash
python3 scripts/evaluate_e4_transport.py "$NFL_E4_RUN"
printf 'delay\n' > "$NFL_E4_RUN/transport-mode.txt"
# No browser: gerar BAL–DAL e selecionar NE–JAX antes da resposta.
printf 'drop-once\n' > "$NFL_E4_RUN/transport-mode.txt"
# No browser: gerar NE–JAX uma vez; atualizar histórico e recuperar, sem novo clique de geração.
```

O harness fixa loopback/destino 18085 e não repete requests. `transport.jsonl` permite conferir dois POSTs e a resposta descartada. Retornar a `normal` ou reiniciar a API direta antes de outros testes. Para indisponibilidade, Ctrl-C somente na API própria; atualizar histórico, reiniciar, atualizar novamente. Encerre os processos próprios no final.

Ampliação de texto, com a UI própria ativa e viewport fixo:

```bash
cp web-ui/local-editorial/style.css "$NFL_E4_RUN/style-normal.css"
cat docs/plans/visual-v1/e4/text200.css >> web-ui/local-editorial/style.css
# Inspecionar 1440 e 320, medir estilos computados: as famílias registradas devem dobrar.
# Enter/Tab/setas; verificar rótulos, badge, valores e reflow. Não alterar a fonte durante essa etapa.
cp "$NFL_E4_RUN/style-normal.css" web-ui/local-editorial/style.css
```

Restaurar somente se não houver edições concorrentes nesse stylesheet. A sobreposição é específica desta baseline e dos tamanhos documentados, não um simulador universal de zoom. Zoom nativo do navegador e leitor de tela continuam fora da evidência coletada.

Auditoria de módulos do build público, sem nova dependência:

```bash
node --input-type=module <<'JS'
import { build } from './web-ui/node_modules/vite/dist/node/index.js';
const modules = [];
await build({root:process.cwd()+'/web-ui',configFile:process.cwd()+'/web-ui/vite.config.ts',
  plugins:[{name:'module-audit',moduleParsed(module){modules.push(module.id);}}]});
const local = modules.filter(id=>/local-editorial\/|features\/analysis-visual\/|contracts\/visual-analysis\//.test(id));
if (local.length) throw new Error(local.join('\n'));
console.log('PASS: public build has no local modules', modules.length);
JS
```
