# NFL Sideline · Refinamento v2

Implementação local em `codex/broadcast-experience-refinement-v2`, partindo exatamente de `3e5f1fded3c00be429642a5c5d353c5410122a92`. Código e testes no commit `4b3feec`; este diretório reúne o plano anterior à implementação, procedência e evidências. Não houve merge, push ou deploy.

[Abrir a central v2](http://127.0.0.1:18087/?round=7) · [Abrir o recorte solicitado](http://127.0.0.1:18087/confronto/dallas-new-england?round=7&period=second&play=rush) · [Comparar com v1](http://127.0.0.1:18086/?round=7).

## O que mudou

Preservados cenário ardósia, azul/vermelho dos times, logos, placar, Archivo/Roboto Condensed e painéis claros contínuos. A leitura específica passou para imediatamente depois dos gráficos. A tabela inferior complementa com volume e jardas; a nota de defesa virou uma definição curta. Contagens equivalentes aos gráficos abrem antes das definições nos detalhes. Saíram a faixa genérica e a repetição da taxa de sucesso na tabela de volume.

Na central, a ação principal passou para depois da manchete, antes do parágrafo e dos números. É um link explícito, com foco visível e sem região de clique oculta. A lista compacta agora reúne os outros três jogos da rodada 7. O arquivo identifica as outras rodadas.

## Comparação verificável

| Problema | Antes | Depois |
| --- | --- | --- |
| Segundo tempo, corrida DAL–NE | “O chão também move a posse.” | “NE soma valor; DAL perde.” Explica EPA positivo de NE e negativo de DAL; apoio de 0,160 EPA/jogada, contexto e amostras próximos. |
| Parte inferior da mesa | Tabela repetia sucesso; nota defensiva repetia jardas; frase genérica em outra faixa | Fato interpretado primeiro, volume depois; definições e contagens expansíveis. Mesmo painel claro. |
| Acesso principal em 390 px | Topo em y=858,2 | y=670,9; botão completo até aproximadamente y=719 em viewport de 844 px. |
| Acesso principal em 320 px | Topo em y=874,8 | y=632,5. Fontes e identidade preservadas. |
| Logo NE em 1280 px | Avançava aproximadamente 34,6 px além da identidade | Logo inteiro; placar, nome e imagem distribuídos dentro da identidade, sem sobreposição. |
| Menu ao entrar em BAL–DAL pelo arquivo da rodada 7 | Apontava para DAL–NE | Mantém BAL–DAL e `period`, `play`, `details`; retorno continua na rodada 7. Breadcrumb separa “Central · rodada 7” e “Duelo da rodada 6”. |

Capturas completas: síntese e parte inferior [antes](evidence/before-synthesis.png) / [depois](evidence/final-matchup-1440.png); central 390 [antes](evidence/before-home-390.png) / [depois](evidence/final-home-390.png); central 320 [antes](evidence/before-home-320.png) / [depois](evidence/final-home-320.png); logo 1280 [antes](evidence/before-1280.png) / [depois](evidence/final-home-1280.png). Medições: [reprodução](evidence/before.json), [responsividade final](evidence/final-responsive.json).

## Regras pequenas de apresentação editorial

`web-ui/broadcast-experience/editorial.ts` recebe jogo, período e fundamento. Usa `summarize`, `mean` e `successRate`, as mesmas funções dos gráficos/tabelas. Devolve decisão, título, frase, contexto, amostras e apoios numéricos estruturados. Não consulta LLM, API, backend ou histórico externo.

1. Pré-jogo não oferece resultado nem amostra da partida. Fonte ausente impede a comparação completa; amostra inferior a 10 jogadas por ataque impede a leitura comparativa. Zero no denominador não vira taxa de 0%.
2. EPA e frequência de sucesso em direções opostas geram uma leitura de divergência, inclusive com sinais de EPA opostos. Não escolhe vencedor geral.
3. Na visão de todos os fundamentos, vantagens distintas no passe e na corrida são explicitadas quando ambas têm amostra suficiente. Com sinais opostos, identifica quem adicionou e quem perdeu valor.
4. Médias iguais com três casas não recebem ordem. Diferença de até 0,010 EPA/jogada é descrita como próxima; sucesso usa proximidade de 2 p.p. São limites de apresentação desta simulação, sem significância estatística implícita.
5. Nos demais casos, descreve a maior média, zero ou perda de valor dos dois ataques. Quando o outro ataque tem pelo menos cinco jogadas a mais, distingue volume e eficiência. Apoios mostram diferenças úteis, sem repetir todos os valores do gráfico.

Os nove recortes de DAL–NE produziram leituras vinculadas à seleção; [interações registradas](evidence/interactions.json). BAL–PIT demonstra [maior EPA com menor frequência de sucesso](evidence/divergent-metrics.png). A função permanece restrita ao diretório sintético; nenhum contrato/editorial do produto real foi alterado.

## Cenários e origem dos números

Tudo está em `web-ui/broadcast-experience/fixtures.ts`. Contagens e somas por tempo/fundamento originam médias, taxas e agregados. O placar deriva dos quartos. Componente ausente deixa indisponível todo agregado que depende dele, sem usar outro tempo como substituto. A identificação “Demonstração · dados simulados” continua persistente no cabeçalho.

Rodada 7: DAL–NE 27–24; BAL–PIT 24–21; GB–CHI pré-jogo; KC–BUF 21–24 com passe de BUF sem fonte no segundo tempo. Oito equipes distintas. Rodadas 6 e 8 mantêm os duelos anteriores no arquivo. [Central completa 1440](evidence/final-home-1440.png).

Pré-jogo usa identidade, local e kickoff demonstrativo, sem vencedor, placar, gráficos, métricas históricas ou seletores sem aplicação: [desktop](evidence/final-pregame-1440.png), [390](evidence/final-pregame-390.png), [320](evidence/final-pregame-320.png).

Ausência mantém o dado de KC visível e identifica BUF como “Sem fonte”, sem barra/taxa de zero ou frase comparativa. Ações explícitas levam a corrida do mesmo tempo ou passe do primeiro tempo: [desktop](evidence/final-missing-1440.png), [390](evidence/final-missing-390.png), [320](evidence/final-missing-320.png).

Escala de EPA começa em −0,20…+0,40 e se amplia em passos de 0,20, sempre comum às séries do recorte. KC tem +0,500 no passe do primeiro tempo e −0,300 no segundo: limites passam a +0,60 e −0,40 respectivamente. [Exemplo de ampliação](evidence/axis-expanded-first-pass.png). Valores assinados e leitura tabular preservados. Logos adicionais são somente cinco PNGs locais da fonte ESPN já documentada no projeto; [procedência](ASSETS.md) e [hashes](assets.json).

## Rodadas reais de refinamento

- **Síntese e consistência:** reproduzi a frase genérica; integrei interpretação e volume no painel; revisei a precedência para divergência EPA/sucesso não ser escondida por sinais opostos. [Captura da rodada 1](evidence/round1-synthesis.png), testes de decisão/apoios em `editorial.test.ts`.
- **Composição e responsividade:** antecipei a ação sem reduzir fontes; ajustei proporção dos logos. [Rodada 2 em 1280](evidence/round2-home-1280.png) e [390](evidence/round2-home-390.png). A revisão final encontrou placar quebrando em 1200 e overflow no arquivo em 1100; ambos foram corrigidos e capturados novamente. Texto a 200% revelou sobreposição logo/placar, resolvida com distribuição flexível.
- **Navegação e estados:** percorri todos os destinos pela interface, menu, retorno, recarga e ações para recortes completos. [Rodada 3 pré-jogo](evidence/round3-pregame-1440.png), [ausência](evidence/round3-missing-1440.png). Reduzi repetição e encurtei a manchete do pré-jogo após inspeção mobile. Capturas `final-*` representam os ajustes concluídos.

## Verificações

- Frontend: **165 testes em 15 arquivos**, lint, build experimental e build público passaram. As cinco falhas esperadas legadas (`it.fails`) estão preservadas; não foram corrigidas. [Logs de testes](evidence/tests.txt), [lint](evidence/lint.txt), [experimental](evidence/experimental-build.txt), [público](evidence/public-build.txt).
- Testes novos cobrem recortes distintos, apoios e vínculo com seleção, divergência EPA/sucesso, empate/precisão/proximidade, ausência/amostra zero, pré-jogo com resultado anexado acidentalmente, origem versus duelo atual, consistência de contagens e escala. Não são snapshots de HTML.
- Central em 1100, 1200, 1280, 1366, 1440, 390 e 320: logos contidos, sem sobreposição ou overflow horizontal. Outras aberturas em mais dez combinações e formatos novos da mesa em quinze combinações: [aberturas](evidence/final-logo-formats.json), [novos logos](evidence/logo-formats.json). Nomes completos, inclusive New England e Kansas City.
- Seis destinos acessados e retorno à seleção anterior: [destinos](evidence/destinations.json). Menu BAL–DAL com origem 7, recarga, detalhes abertos e navegação direta sem origem: [prova estruturada](evidence/navigation.json), [captura](evidence/navigation-current-origin.png).
- Teclado: skip link focou `main`; seleção por Tab/Espaço; detalhes por Enter; foco visível de 3 px. [Captura](evidence/keyboard-focus.png). Redução de movimento respeitada. [Medições](evidence/accessibility.json).
- Ampliação: zoom visual CDP `pageScaleFactor=2`, além de teste separado com fonte raiz de 16→32 px para reflow real de texto em 1440 e 390. Não foi alegado teste de zoom por atalho nativo. [Zoom](evidence/zoom200.png), [texto 200% final desktop](evidence/final-text200-home-desktop.png), [mesa mobile](evidence/text200-matchup-mobile.png), [medição final](evidence/final-text200.json).
- CDP confirmou fontes efetivamente renderizadas: Archivo em nomes/manchetes/leitura; Roboto Condensed nos valores. [Registro](evidence/fonts.json). Sem erros de console na leitura final; recursos de runtime somente em `127.0.0.1:18087`.
- [Isolamento](evidence/isolation.json): paths protegidos sem alterações ou arquivos novos; JS/CSS públicos com os mesmos hashes da base. [Build sob variáveis adversas](evidence/production-proof.txt) idêntico ao normal. Backend, ETL, contratos, snapshots e laboratório preservados. Checkout original e v1 continuam nos mesmos HEADs e sem alterações rastreadas; servidor v1 permanece em 18086.

## Inicialização, encerramento e limites

Worktree gerenciada: `/Users/pedrocollet/.codex/worktrees/broadcast-experience-refinement-v2/NFL Sideline`. Branch `codex/broadcast-experience-refinement-v2`. Servidor próprio Vite deixado em `127.0.0.1:18087`, PID **770** nesta sessão; host loopback, porta estrita e sem proxy. Dependências locais reutilizadas por symlink ignorado; não houve instalação de framework ou biblioteca.

```bash
cd '/Users/pedrocollet/.codex/worktrees/broadcast-experience-refinement-v2/NFL Sideline'
npm --prefix web-ui run experience:dev
# Para encerrar apenas o servidor deixado nesta sessão:
kill -TERM 770
# Se iniciado no seu terminal, use Ctrl+C naquele terminal.
```

Comandos de verificação reproduzíveis no [README da entrada](../../../web-ui/broadcast-experience/README.md). O [manifesto de evidências](evidence/manifest.json) registra dimensões, bytes e SHA-256. A entrega termina com dois commits locais, árvore limpa e sem publicação.

Limites: são seis duelos estáticos; pré-jogo não evolui automaticamente nem oferece histórico. A ausência demonstrada é parcial e localizada; amostra zero/curta e empate são cobertos por testes de regras. As regras descrevem a amostra e não estimam incerteza, causalidade ou desempenho geral. A mesa mobile continua longa por preservar gráficos, tabelas e destinos; definições ficam recolhidas. Não houve estudo com pessoas ou nova aprovação visual do usuário nesta rodada.
