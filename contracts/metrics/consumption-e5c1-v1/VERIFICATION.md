# Verificação e limites da candidata

Comandos na raiz da worktree, Python 3.14.6 e jsonschema existentes; sem instalação:

```bash
python3 -B contracts/metrics/consumption-e5c1-v1/verify.py
python3 -B -m unittest discover -s contracts/metrics/consumption-e5c1-v1 -p 'test_*.py'
git diff --check fed166d1682a818b0cca8dd11325ff23ea672c07
git diff --name-only fed166d1682a818b0cca8dd11325ff23ea672c07 -- . ':!contracts/metrics/consumption-e5c1-v1'
```

Resultado final registrado em [verification.json](verification.json): schema
Draft 2020-12 válido; **34 observações, 17 cenários/476 decisões, 12 inválidos e
12 testes de propriedades**. As três contraprovas históricas são sintéticas.
O catálogo E5a confirma a cobertura das quatro famílias/22 IDs; os vetores
numéricos usam defesa/passe e a política por família aplica-se aos demais IDs.
Isso não é teste exaustivo de todos os papéis/fundamentos ou de séries reais.

Inválidos: campo extra, ausência promovida a zero, denominador zero, soma float,
contagens divergentes, taxa de cobertura inventada, EPA zero sem observações,
modelo inventado em UNKNOWN, completude promovida sem testemunha, semana fora
do pedido, vínculo de modelo contraditório e conflito de integridade com números.
Os testes distinguem erros de schema e de semântica. Escolha duplicada por jogo
também é rejeitada. As decisões recusadas explicitam missingRequirements.

O verificador confere estrutura, valores e contagens da projeção, identidade,
mapa de modelo por FILE, lacunas, testemunhas dos exemplos e cronologia sintética.
Não recalcula PBP, autentica uma autoridade ou confere que evidências sintéticas
existem num archive real. Os estados aceitos das fixtures são premissas marcadas.
Não executa seleção PIT: o teste de correção tardia valida a expectativa e a
projeção congelada, não uma implementação futura. Garantias de runtime aceito
continuam pertencendo às evidências anteriores, preservadas, não reexecutadas.

Preservação: diff completo de todos os caminhos rastreados contra a base permite
mudanças apenas neste novo diretório, incluindo schema/algoritmos/adapter/writer,
SQL/Java/frontend/snapshots/aprovações/workflow e relatórios históricos. Checkout
original conferido contra inventário anterior: mesmo HEAD/status e hashes dos
36 arquivos não rastreados, sem ler .env. Esse inventário é local; o relatório
registra seus hashes e resultado, não transforma arquivos históricos em fixtures.
A worktree partiu detached em fed166d, limpa; branch codex/metrics-consumption-e5c1
foi criada nela. Nenhum caminho do checkout original foi editado.

Checks de Git não provam imutabilidade de banco ou archive externo; nenhum deles
foi acessado. Não se repetiram suites ETL/Java/SQL/visual nem gates documentais de
outras bases, pois seus componentes não mudaram. Não houve aquisição/modelos,
.env, migrations, novos registros operacionais, push, merge em main ou deploy.

Aceite do orquestrador ainda pendente. O pacote é somente candidato e não foi
conectado, publicado ou registrado como aprovação do produto.
