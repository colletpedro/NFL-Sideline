# Visitas e contexto do EPA da red zone

Ajuste local sobre `887d9600c59bda8f23561e2d18fce7300f6c8b7d`, na mesma worktree/branch `codex/broadcast-score-curve-v2`. A porta 18111 e seu processo foram mantidos; a interface recebeu o ajuste por HMR. Sem merge, push ou publicação.

[Abrir CIN × BAL, no EPA da red zone](http://127.0.0.1:18111/?view=matchup-season&game=2026_07_CIN_BAL&rank=season#mr-redzone-epa).

## Resultado

- “Timeline de eventos” substitui “Ver sequência por escrito”. Foram removidos os expansíveis “Conferir placares, eventos e evidências” e “Quando uma campanha entra na red zone?” da experiência atual.
- O antigo expansível técnico do EPA dá lugar a **Jogadas por visita à red zone**: situação inicial observada dentro das 20, jogadas elegíveis em ordem e resultado da campanha. Ao fim de cada ataque, a soma e o denominador originais explicam a média.
- **As jogadas que mais pesaram** fica visível. Cada ataque destaca seu maior EPA em valor absoluto, com contexto expansível de descida, distância, relógio e descrição original. Empates são informados; mostra-se a primeira na ordem do recorte. A regra vale tanto para contribuições positivas quanto negativas.
- A mesma composição está disponível nas páginas de time, com semana e participantes identificando as visitas de jogos diferentes. As entradas anteriores continuam com sua apresentação própria.

CIN × BAL: CIN tem cinco visitas e dez jogadas válidas, EPA/jogada +0,983; BAL tem três visitas e dez jogadas válidas, EPA/jogada −0,724. O destaque de BAL é a jogada **2836**, EPA original **−3.114080941246357**, 4ª para 2, a 12 jardas da end zone, Q4/15:00. A fonte descreve passe incompleto de T. Huntley para J. Cuevas. Não se atribui causa além do registro.

[Contexto do EPA](evidence/final-epa-context.png) · [Visitas desktop](evidence/visits-1440.png) · [Visitas mobile](evidence/visits-390.png).

## Conferência

Não foi necessário criar outro pacote ou enriquecer o backend. As evidências das campanhas já continham os campos solicitados. O adaptador junta essas evidências às unidades de EPA por `game_id:play_id`, recusando unidades sem vínculo, duplicadas ou com identidades/posição incompatíveis. Uma campanha permanece uma visita mesmo com saída e reentrada.

A conferência independente confrontou **723 campanhas, 2.096 jogadas elegíveis e 2.521 contextos** com o Parquet congelado. As 40 campanhas com saída/reentrada observada continuam únicas. Descidas, distâncias, descrições e relógios foram conferidos; para o relógio, o restante do jogo e o quarto reproduzem exatamente o restante do quarto da fonte, inclusive prorrogação. Somas e médias racionais originais permanecem intactas. [Resultado](checks/reconciliation.json).

**370 testes frontend**, TypeScript, lint sem erros (um aviso herdado), nove builds experimentais e dois builds públicos passaram. As cinco falhas esperadas legadas permanecem. Os testes novos cobrem todos os jogos e os 64 agregados ofensivos/adversários, o caso 2836, ausência de oportunidades, EPA zero, empates e recusa de vínculos incompatíveis.

**142 respostas HTTP** reproduziram exatamente os bytes dos pacotes existentes. Pins de curva, cronologia e coleção W1–7 preservados; JS/CSS públicos idênticos. [Isolamento](checks/isolation.json).

No navegador: visitas e destaques em 1440/390/320 px, fonte raiz 16 e 32 px, sem overflow horizontal nas 12 combinações verificadas. Expansão por Enter conferida. CIN e seus adversários foram também conferidos na página de time. [Layout](evidence/layout.json) · [Teclado](evidence/keyboard.json). Não houve nova avaliação humana ou teste de toque físico.

## Reprodução e operação

A partir da raiz desta worktree:

```bash
# Reutiliza os mesmos pacotes locais e a mesma porta estrita.
docs/plans/broadcast-score-curve-v2/run-local.sh

# Só se desejar encerrar o processo atual, confirme antes sua identidade:
lsof -nP -a -p 83042 -iTCP:18111 -sTCP:LISTEN
kill -TERM 83042

# Verificações reproduzíveis, com as fontes locais documentadas:
sh docs/plans/broadcast-redzone-visits-v1/checks.sh
PYTHONPATH=etl-pipeline/src PYTHONDONTWRITEBYTECODE=1 \
  '/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' -B \
  docs/plans/broadcast-redzone-visits-v1/verify.py
python3 docs/plans/broadcast-redzone-visits-v1/check-isolation.py
```

Os logs ficam em `checks/`. O acervo continua descritivo: modelo EPA, completude e disponibilidade histórica permanecem desconhecidos. O texto original das jogadas está em inglês, identificado como descrição da fonte. Visitas e jogadas são populações diferentes; a taxa de TDs usa campanhas, o EPA/jogada usa somente as jogadas elegíveis com EPA válido.
