# Validação operacional e apresentação — concluída

Execução iniciada em 2026-10-02 e inspeção visual concluída em 2026-10-05. A geração offline
e a API local foram verificadas com HTTP real em loopback, sem credenciais, banco ou Gemini.
Esta entrega não conecta o frontend principal à API e não publica análises.

## Alteração de apresentação

Renderer **controlled-claims-v5.0.2**. Seletor **2.0.0**, claims **5**, serviço **1.0.0** e
artefato **3** permanecem. Um extremo que exige desigualdade agora é identificado explicitamente:

- Antes: `faixa semanal de 0 < EPA < 0,0005 a +0,116 EPA`.
- Agora: `faixa semanal: mínimo (0 < EPA < 0,0005); máximo (+0,116 EPA)`.

O limite continua sendo exclusivamente de formatação. Sinais, valores, recortes, seleção e
claims não mudaram. Faixas comuns continuam no formato anterior. A identidade do resultado
inclui a nova versão do renderer. O JAR anterior e os renderers foram copiados para [baseline](baseline/)
antes do rebuild; os artefatos históricos não foram sobrescritos.

A sonda numérica do harness agora separa ataque e defesa pelo nome da defesa, sem confundir
o ponto e vírgula dentro de uma faixa com o separador entre equipes. A página obtém a versão
do renderer dos resultados persistidos, evitando uma etiqueta fixa desatualizada.

## HTTP real

[Verificação completa](http-run-01/verification.json), [requisições/respostas](http-run-01/http/).

- **75 requisições reais**, todas com o status esperado.
- **21/21 casos** gerados por POST, consultados por GET e iguais à CLI em textos e identidade.
- Claims e seleção iguais ao lote histórico nos **21/21** casos.
- Apenas o `alerta_vermelho` de LV–NO mudou na comparação textual, devido à faixa acima.
- **21/21 resultados** recuperados com o mesmo conteúdo após encerrar e reiniciar o servidor.
- Quatro POSTs concorrentes produziram quatro tentativas distintas e uma identidade semântica.
- Segundo processo usando o mesmo armazenamento foi recusado.
- Origin, Host incorreto, body, query e caminho codificado recusados com 400; jogo/resultado
  inexistentes com 404; método incompatível com 405. Erros sanitizados, sem CORS e com no-store.
- Ambos os processos Java foram encerrados (SIGTERM, saída 143), com liberação do armazenamento.

O bind inicial no sandbox foi negado. A execução restrita autorizada em loopback permitiu os
testes reais; não se substituiu transporte por simulação nesta verificação. O ambiente dos
subprocessos contém apenas PATH e LANG, sem leitura de `.env`.

## Navegador e apresentação

[Página estática](inspection.html), [verificação do navegador](browser-verification.json),
[desktop](desktop.png), [tela estreita](mobile.png), [exemplo LV–NO](range-example.png).

Verificação no navegador integrado, carregando a página por HTTP real:

- 21 cartões, quatro blocos por análise e versão 5.0.2 visível.
- **19 opções de filtro** verificadas; combinações, contagem e estados vazios corretos.
- Evidências abertas e fechadas em desktop e tela estreita.
- Viewports **1440 × 1000** e **390 × 844**: quatro colunas e uma coluna, respectivamente.
- Sem overflow horizontal da página ou dos blocos medidos na tela estreita.
- Sem erros ou avisos de console registrados na inspeção.
- Faixa de LV–NO corrigida confirmada no texto renderizado.

Não foi emulado um aparelho físico. Esta inspeção verifica layout responsivo e funcionamento;
os textos longos, nomes repetidos e avisos continuam sendo limitações editoriais conhecidas.
Não houve redesenho ou retuning das regras. A página de inspeção lê resultados já gerados;
ela não é um cliente de geração da API.

O CLI agent-browser não estava instalado; a inspeção utilizou o navegador integrado via
computer use. A revisão automática foi interrompida por limite de uso em 02/10; os testes
visuais foram retomados e concluídos em 05/10. Não há pendência de navegador desta entrega.

Os servidores temporários de inspeção também foram encerrados. A aba pode continuar exibindo
o documento carregado; para recarregar, inicie novamente o servidor com o comando abaixo.
O servidor final foi verificado separadamente: HTML 200, arquivos adjacentes e rota não
suportada 404, com CSP sem conexões. [Evidência](page-server-verification.json).

## Testes e integridade

- [Java 21 clean verify](java21-clean-verify.log): **116 testes**, zero falhas, erros ou ignorados.
  O JAR não mudou entre esse gate, a execução HTTP e a retomada da inspeção.
- [Harness Python](python-tests.log): **12 testes**, aprovados.
- [Sondas HTML/JavaScript](page-source-tests.json): 21 cartões e 19 opções; complementam o
  navegador real, não são apresentadas como teste visual.
- Reconstrução da página com `build_operational_inspection.py`: HTML idêntico byte a byte.
- 21 resultados sem problemas nas sondagens estruturadas de atribuição, números e limitações.
- `git diff --check` aprovado. [Integridade final](integrity.json) e [identidade](implementation-identity.json).

Uma primeira montagem do journal para métricas omitiu metadados de coorte e gerou KeyError
antes de produzir métricas. O journal incompleto foi preservado com nome de preflight; seus
metadados foram corrigidos a partir do manifesto conhecido, sem alterar contextos ou saídas.
O construtor reproduzível agora valida o manifesto e recusa sobrescrita divergente.

## Reprodução

Da raiz, com Java 21, dependências Maven locais e permissão de loopback. Não carregar `.env`.
Use novos diretórios para cada execução; preserve o JAR de uma baseline antes de reconstruí-lo.

```bash
export JAVA_HOME=/opt/homebrew/opt/openjdk@21/libexec/openjdk.jdk/Contents/Home
export PATH="$JAVA_HOME/bin:$PATH"
mvn -f core-api/pom.xml -o clean verify
python3 scripts/validate_local_operation.py editorial/validacao-operacional-nova
python3 scripts/build_operational_inspection.py \
  editorial/validacao-operacional-nova editorial/inspecao-operacional-nova
python3 scripts/serve_editorial_inspection.py \
  editorial/inspecao-operacional-nova/inspection.html --port 18082
```

Abra `http://127.0.0.1:18082/inspection.html`; Ctrl-C encerra a inspeção. O verificador HTTP
encerra seus próprios servidores automaticamente. Para reutilizar somente esta página, execute
o último comando com `editorial/operational-validation-v1/inspection.html`.

## Estado e próximos limites

**Geração offline e API local implementadas e operacionalmente verificadas.** A próxima etapa
pode integrar uma interface local de desenvolvimento por uma decisão explícita de transporte;
a API atual recusa Origin e não fornece CORS. Não alterar isso silenciosamente para conectar
o frontend. A integração principal e a publicação continuam fora desta entrega.

Os 17 jogos reais e quatro exemplos sintéticos já eram conhecidos. Esta não é avaliação
independente, comprovação de qualidade editorial ou capacidade preditiva. Nada foi enviado
a um provedor de geração, publicado, aprovado automaticamente ou gravado em banco remoto.
Frontend, snapshots, aprovações e avaliações anteriores foram preservados; sem commit/push/deploy.
