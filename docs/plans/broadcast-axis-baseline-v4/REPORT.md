# Eixo de EPA e referência visual experimental

Base limpa conferida: `9c43b06c91c146357009f28774c693ddfd78a306`. Worktree gerenciada `/Users/pedrocollet/.codex/worktrees/broadcast-axis-baseline-v4/NFL Sideline`, branch `codex/broadcast-axis-baseline-v4`. Implementação em `840e3603920b3db15dca44116d2072f5a8528d4f`; documentação e evidências em commit separado. Versões e servidores anteriores preservados. Sem integração real, merge, push ou deploy.

[Central v4](http://127.0.0.1:18089/?round=7) · [Eixo ampliado](http://127.0.0.1:18089/confronto/kansas-city-buffalo?round=7&period=first&play=pass) · [Pacote de referência visual v1](../../visual-reference/v1/README.md).

## Correção

Reproduzi na v3, antes de editar, o recorte KC–BUF do primeiro tempo/passe a 320 px. +0,40 terminava em x=193,74 e +0,60 começava em x=187,72: sobreposição de **6,02 px**. [Antes](evidence/axis-before-320.png), [medição anterior](evidence/axis-before.json).

A solução usa três rótulos: **mínimo, zero e máximo**, sem reduzir fonte. `epaAxisLabels` filtra os ticks de `epaScale`; linhas intermediárias continuam presentes. O alinhamento dos extremos permanece interno ao eixo e o zero continua em sua posição quantitativa. [Depois em 320](evidence/axis-positive-320.png), [página completa](../../visual-reference/v1/images/axis-expanded-320.png).

Somente `Charts.tsx`, `chartScale.ts` e o novo `chartScale.test.ts` mudaram no código. A função original de domínio/posicionamento está intacta. Não houve mudança de CSS, fixture, texto ou regra editorial, navegação, filtros, ausência ou pré-jogo. Valores do exemplo continuam KC +0,500 e BUF +0,250; barras começam em 25% e têm larguras de 62,5% e 31,25%, idênticas à v3. [Prova de preservação e hashes](evidence/preservation.json).

## Verificação no navegador

| Recorte | Domínio | Evidência |
| --- | --- | --- |
| DAL–NE, segundo tempo/corrida, valores nos dois lados do zero | −0,20…+0,40 | [320](evidence/axis-initial-320.png), [390](evidence/axis-initial-390.png) |
| KC–BUF, primeiro tempo/passe | −0,20…+0,60 | [320](evidence/axis-positive-320.png), [390](evidence/axis-positive-390.png), [1024](evidence/axis-positive-1024.png), [1440](evidence/axis-positive-1440.png) |
| KC–BUF, segundo tempo/passe, BUF sem fonte | −0,40…+0,40 | [390](evidence/axis-negative-missing-390.png), [tela completa](../../visual-reference/v1/images/missing-390.png) |
| KC–BUF, jogo completo/todos, cobertura parcial | −0,20…+0,40 | [320](evidence/axis-initial-missing-320.png) |

Cada caso foi medido em **320, 390, 1024 e 1440 px**: 16 combinações sem colisão, sem overflow horizontal da página em fonte padrão. O menor espaço entre rótulos foi **5,18 px**, entre o mínimo e zero no domínio positivo a 320 px. Fonte do eixo mantida em 0,6875 rem. [Coordenadas, valores e geometria](evidence/axis-normal.json).

Texto ampliado: fonte raiz passou de 16 para 32 px, pelo navegador, nos três primeiros casos em 320 e 1440, e no domínio positivo em 390. Foram sete combinações; menor intervalo entre rótulos de **8,38 px**, sem colisão. Não se trata de teste de zoom por atalho nativo. [Seis casos](evidence/axis-text200.json), [390](evidence/axis-text200-390.json). Estilos de verificação removidos ao finalizar.

O eixo permanece correto com série ausente: não há barra inventada para BUF. A tabela expandida do primeiro tempo/passe foi conferida no navegador: KC 20 jogadas, 13/20, +0,500; BUF 18 jogadas, 11/18, +0,250. A leitura tabular e os textos das séries permanecem completos. Sem erros de console na inspeção final.

**Pendências separadas:** com texto a 200%, o gráfico conserva rolagem horizontal local já existente. Em 320 px, um texto auxiliar de “Volume do recorte” também produz largura de página de 362 px, reproduzida na v3 e na v4. Não é causada pelos rótulos; CSS e componente da tabela não mudaram. [Medição comparativa](evidence/text200-existing-overflow.json). Detalhes e escopo no [documento de limites](../../visual-reference/v1/LIMITS-AND-NEXT.md).

## Checks e isolamento

- **167 testes em 16 arquivos**, lint, build experimental e build público passaram, uma vez após a implementação final. As cinco falhas esperadas legadas permanecem preservadas. [Testes](evidence/tests.txt), [lint](evidence/lint.txt), [experimental](evidence/experimental-build.txt), [público](evidence/public-build.txt).
- Os dois testes novos verificam extremos/zero, ordem, unicidade, pertencimento ao domínio e aos ticks, ausência de mutação e posições dos valores antes/depois da seleção. Não reproduzem constantes de CSS.
- Verificação de isolamento herdada passou: paths protegidos intactos; JS/CSS públicos mantêm os hashes da base estável. [Resultado](evidence/isolation.json). Fixtures, regras/textos editoriais, navegação e materiais têm comparação byte a byte com a v3 na prova de preservação. Contratos, snapshots, consumidores, laboratório real, backend, ETL e publicação não foram tocados.

## Referência consolidada

O [pacote v1](../../visual-reference/v1/README.md) reúne identidade e valores existentes, mapa dos componentes, nove capturas com rotas/dimensões/hashes, limites da simulação e fronteira documental para uma futura observação real. A implementação adotada é o commit `840e3603920b3db15dca44116d2072f5a8528d4f`. O feedback do usuário e a revisão do orquestrador são atribuídos ao briefing; não há nova aprovação humana ou estudo de compreensão alegado.

Os comandos de inicialização e reprodução estão em [SCREENS.md](../../visual-reference/v1/SCREENS.md). Servidor próprio Vite em `127.0.0.1:18089`, PID **15045** nesta sessão. Iniciar na raiz desta worktree: `npm --prefix web-ui run experience:dev -- --port 18089`. Encerrar apenas o servidor deixado: `kill -TERM 15045`; se iniciado no seu terminal, Ctrl+C naquele terminal. V1/v2/v3 seguem em 18086/18087/18088.

O [manifesto técnico](evidence/manifest.json) identifica os arquivos de evidência; o [manifesto da referência](../../visual-reference/v1/manifest.json) identifica os estados adotados. A entrega termina com dois commits locais focados e árvore limpa.
