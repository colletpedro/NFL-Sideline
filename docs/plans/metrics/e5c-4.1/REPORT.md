# E5c-4.1 — três experiências para comparar

As propostas funcionais estão em http://127.0.0.1:18083/. No topo, use **A Estádio**, **B Transmissão** ou **C Prancheta**. O recorte permanece o mesmo. **E5c-4 anterior** permite voltar à candidata precedente. Uma sessão nova começa em BAL, ataque geral, W1–2/2026; seleção válida já salva é preservada.

## Iniciar com os dados reais
```bash
cd '/Users/pedrocollet/.codex/worktrees/visual-reading-e5c4/NFL Sideline'
NFL_OBSERVATION_CONFIG='/Users/pedrocollet/Downloads/NFL Sideline/docs/plans/metrics/e5c-3r/lab-config.json' \
NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' \
npm --prefix web-ui run editorial:dev
```
Servidor local mantido para experimentação ao entregar. Ctrl+C encerra a execução no terminal que o iniciou. Não exige banco, aquisição ou LLM. Production permanece estática.

## Diferenças e recomendação
| Proposta | Composição | Gráfico central | Exploração e limite |
| --- | --- | --- | --- |
| A Estádio | Palavra gigante, luz difusa e campo em perspectiva; controles no primeiro plano | Área proporcional de EPA positivo e zero/negativo | Maior presença visual; mobile prioriza gráfico antes dos controles |
| B Transmissão | Faixa de identidade, rail lateral e números de apoio | Duas faixas com denominador e escala comuns | Recomendada para uso frequente; no mobile tem mais altura que A |
| C Prancheta | Ambiente de campo esquemático, anotação serifada, controles laterais | Volume observado por jogo | Melhor para investigar a composição do arquivo; quatro jogos alongam a página |

Recomendo **B** por leitura e navegação frequente. Nenhuma direção foi escolhida em definitivo: as três continuam disponíveis. A abre primeiro por ordem de apresentação, não como aceite.

[DIRECTIONS.md](DIRECTIONS.md) contém esboços, referências realmente acessadas e tabela dos campos/denominadores dos gráficos. [ITERATIONS.md](ITERATIONS.md) registra problemas e correções. Composição CSS/SVG original, sem copiar fotografia, vídeo ou fonte comercial. Impact e Georgia dependem das fontes de sistema, com fallback; outros sistemas podem alterar um pouco a textura tipográfica.

## Comparação visual
| | Desktop 1440 × 900 | Mobile 390 × 844 | Página completa | Defesa DAL | Sem PBP |
| --- | --- | --- | --- | --- | --- |
| A | [A](evidence/A-desktop.jpg) | [A](evidence/A-mobile.jpg) | [A](evidence/A-full.jpg) | [A](evidence/A-defense.jpg) | [A](evidence/A-gap.jpg) |
| B | [B](evidence/B-desktop.jpg) | [B](evidence/B-mobile.jpg) | [B](evidence/B-full.jpg) | [B](evidence/B-defense.jpg) | [B](evidence/B-gap.jpg) |
| C | [C](evidence/C-desktop.jpg) | [C](evidence/C-mobile.jpg) | [C](evidence/C-full.jpg) | [C](evidence/C-defense.jpg) | [C](evidence/C-gap.jpg) |

As medidas indicam viewports solicitados; o capturador pode normalizar pixels/retirar a barra de rolagem na exportação JPEG. Também preservados 320 px, 1024 px, texto 200%, NE POST e sintéticos em `evidence/`. Evidências anteriores da E5c-4 permanecem intactas.

## Validação
- `npm --prefix web-ui test`: 141 testes em 11 arquivos aprovados, incluindo as cinco regressões legadas `it.fails` sem alteração/reclassificação. Log `tests.txt`.
- Após os últimos ajustes de texto, `npm --prefix web-ui test -- local-editorial/observations/directions.test.tsx`: quatro testes de identidade/precisão, aritmética acima de Number seguro, ausência/zero e semântica defensiva. Log `final-tests.txt` (o segundo filtro nominal não encontrou arquivo; apenas os quatro testes indicados executaram).
- `npm --prefix web-ui run lint` e `npm --prefix web-ui run build`: aprovados; logs finais. Revisão React: dados derivados no render, transporte compartilhado, sem novo efeito/fetch por proposta, IDs estáveis nos membros e nenhum pacote novo.
- Build público idêntico com flags VITE adversas; `production.txt`. Build final manteve os mesmos assets `index-BIYXDnRB.css` e `index-BTsQyTsc.js`. Nenhum módulo local incorporado.
- 48 documentos HTTP iguais ao leitor aceito, 12 recusas conferidas: `evidence/http.json`.
- 48 recortes × três propostas = 144 leituras reais no navegador, mesmos números/IDs/denominadores: `evidence/browser-48-three-directions.json`.
- Seleção → documento → troca → detalhes → recarga; troca de proposta sem fetch, foco visível e recarga com recorte persistente: `selection-keyboard-reload.json`, `details-keyboard.json`.
- 320 e 1024 sem overflow, texto 200% com reflow e reduced motion: `responsive.json`, `text200.json`. Detalhes por teclado nas três. Gráficos têm contagens e alternativa textual, não dependem só de cor.
- Fixtures existentes: EPA 0,000, base EPA zero e −<0,001 nas três: `synthetic-browser.json`. Ausência real W3 não vira zero. Não alterados formatador, validação, adapter, leitor, materializador ou contratos. Guardas de sessão, identidade, cancelamento e respostas atrasadas preservadas; testes existentes reutilizados, sem nova campanha de atrasos nesta rodada.

## Limites e compreensão humana
Sem participantes humanos disponíveis. Protocolo pronto: começar com BAL W1–2 e alternar A/B/C; em cada proposta pedir que a pessoa identifique time, papel, fundamento/período, explique gráfico e denominador, localize amostra e limites, mude para defesa/passe, diferencie frequência de eficiência, abra origem e explique por que W3 sem PBP não é zero. Perguntar se é possível prever vencedor e qual composição gostaria de reutilizar. Alternar a ordem entre participantes; registrar falas, hesitações e erros reais, sem inventar tempos ou acertos.

Escolha visual e compreensão humana pendentes. Esta entrega não equivale ao aceite operacional do orquestrador. Dados 2026 históricos W1–2, garantias UNKNOWN preservadas, sem ranking, comparação certificada ou previsão. IDs de jogo ainda aparecem junto às barras C para distinguir registros; nomes de adversários normalizados seriam evolução futura sustentada por campo/contrato apropriado.

## Continuidade
Branch `codex/visual-reading-e5c4`. Base limpa conferida: `0f8762bef1dcc0b5baaf669c797bbdc9ed7813cf`. Bundle ID preservado: `sha256:2fae3be2b1ab7e5799287469ec29b9a98ff652a365ccafcb11b46c55d98ace8a`.
Implementação: `a63bace` (três direções e testes). O commit documental subsequente contém este relatório e as evidências; HEAD final informado na resposta. Sem merge, push, deploy ou publicação.
