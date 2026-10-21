# E5c-4.3 — composição cromática e leitura editorial

Implementada e inspecionada no Chrome local em 20–21/10/2026 (America/Fortaleza). Nova proposta **Transmissão 4.3**, selecionada por padrão em uma sessão nova. **Versões anteriores** preserva 4.2, A/B/C e E5c-4; a troca mantém o recorte. Aceite visual humano e aceite operacional continuam pendentes.

## Identidade da entrega

- Worktree: `/Users/pedrocollet/.codex/worktrees/visual-broadcast-refinement-e5c43/NFL Sideline`.
- Branch: `codex/visual-broadcast-refinement-e5c43`.
- Base conferida antes da edição: `0609db55cdbc830db661ad99b9b643781eff0ba5`.
- HEAD da implementação inspecionada: `565188023446cf29b851c8b28f79019f72bdd13d`.
- Commits locais de código: `1565715` (componentes, temas, prova e testes), `042cc5d` (proporções por time), `5651880` (respiro dos escudos).
- O commit documental seguinte contém este relatório, scripts, logs e capturas; seu HEAD é informado na entrega e pode ser recuperado com `git rev-parse HEAD` nesta worktree.
- Bundle aceito: `sha256:2fae3be2b1ab7e5799287469ec29b9a98ff652a365ccafcb11b46c55d98ace8a`.
- Sessão real: `sha256:a0b4a5b4ffbac39ef3ea827c1c7b0b53a30156aa1a94214da3722630dd3d9e2c`.

## Experimentar e reproduzir

Servidor desta entrega mantido em [127.0.0.1:18084](http://127.0.0.1:18084/). Prova: [tipografia 4.3](http://127.0.0.1:18084/broadcast/type-proof-4.3.html).

A porta 18083 já estava ocupada pelo servidor anterior (PID 88635 no preflight). Ele não foi encerrado. Para reproduzir em paralelo:

```bash
cd '/Users/pedrocollet/.codex/worktrees/visual-broadcast-refinement-e5c43/NFL Sideline'
NFL_OBSERVATION_CONFIG='/Users/pedrocollet/Downloads/NFL Sideline/docs/plans/metrics/e5c-3r/lab-config.json' \
NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' \
node docs/plans/metrics/e5c-4.3/serve-inspection.mjs
```

`serve-inspection.mjs` é um auxiliar de inspeção, fora da entrada normal. Aceita apenas Host/Origin exatos de `127.0.0.1:18084` e adapta esses cabeçalhos em memória para as guardas fixas de 18083, antes dos plugins originais. Reexecuta o reader aceito e congela o catálogo com as mesmas validações. Não implementa um novo contrato de transporte nem altera suas guardas. Ctrl+C no terminal próprio encerra esse servidor.

Quando 18083 estiver livre, a entrada normal continua sendo `npm --prefix web-ui run editorial:dev`, com as mesmas duas variáveis explícitas. O `node_modules` ignorado desta worktree reutiliza por symlink as dependências já existentes no checkout original; nenhum pacote ou modelo foi instalado.

## O que mudou e por quê

| Prioridade | Implementação |
| --- | --- |
| Duas cores por time | Papéis explícitos de placa de nome, placa de escudo, contexto, acento e texto. NE usa navy + região vermelha; DAL usa prata derivada mais escura + escudo/contexto navy; BAL mantém roxo dominante + placa preta e costura dourada. Sem mistura das identidades em degradê. |
| Neutros editoriais | Papel plano `#D6DCE1`, controles `#E9EDF0`, limites `#C9D1D7`, ardósia `#38434B`, tinta `#18232B`, cenário periférico carvão/quente. Gráfico ardósia `#384B5A`, complemento com textura; removida a cor teal desconectada da proposta anterior. |
| Tipografia normal | Barlow normal 700 em nomes/manchete/valores, 600 em rótulos/controles e 400 no corpo. Prova paralela com Plex Sans normal, conteúdo/espaço/tamanhos/pesos equivalentes 700/400. Não há scaleX nem condensada como voz padrão da 4.3. |
| Continuidade | Volume, frequência, precisão, origem e sessão seguem superfícies claras e a mesma tinta/divisórias. Volume usa linhas compactas, números à direita, barras finas proporcionais e identificadores de jogo recolhidos. Nenhum parser de adversário foi introduzido. |

As larguras da placa de escudo são escolhas ópticas por time: BAL 22%, DAL 30%, NE 33% no desktop; 29/30/32% no compacto. Não representam proporções estatísticas nem uma regra universal de identidade.

O cabeçalho, contexto e controles ocupam menos altura. Os conjuntos de ataque/defesa e fundamentos continuam visíveis, com estado pressionado e sublinhado. São botões com `aria-pressed`, sem fingir um padrão de abas com comportamento de teclado que não foi implementado. EPA, base e amostra compartilham linhas alinhadas; o percentual deixou de ser o único suporte à hierarquia.

Modelo EPA UNKNOWN continua junto ao gráfico. Completude, expectativa e conhecimento antes dos jogos ficam em frase curta visível; o texto integral permanece expansível. A inspeção aceita original continua expondo motivos, escopos, frações e identidades completos. Defesa conserva valores permitidos ao ataque adversário; frequência continua sendo distribuição, não qualidade.

## Referências e tipografia verificadas

Lidos o AGENTS.md, Spec.md, estado atual, relatórios 4.1/4.2, contrato E5c-1, transporte E5c-3 e o pacote de handoff indicado. As cinco imagens do refinement-4.3 e as 12 referências originais foram abertas visualmente. O sistema e o handoff foram lidos por caminho absoluto no checkout original, sem incorporar alterações não relacionadas.

As fichas 02/04, o calendário 05 e o lower third Cowboys 10 orientaram separação de planos, alinhamento e contraste; as duas referências tipográficas novas orientaram largura normal, manchete forte e subtítulo regular. Não foram copiados fatos esportivos das imagens. [DESIGN.md](DESIGN.md) registra a direção anterior à implementação e sua evolução.

Os arquivos, licenças e procedência de fontes/logos da 4.2 foram preservados; ver [ASSETS.md anterior](../e5c-4.2/ASSETS.md). Não houve nova aquisição de ativos. Hex de referência continuam sendo registros secundários; prata, preto e superfícies locais são derivações de design, sem certificação de manual oficial vigente. Não identificamos a família exata da ESPN/Josh Pate.

A prova usa Barlow-Regular/Bold.woff2 e IBMPlexSans-Regular/Bold.woff2. Chrome CDP `CSS.getPlatformFontsForNode` confirmou glifos customizados **Barlow-Bold**, **Barlow-Regular**, **IBMPlexSans-Bold** e **IBMPlexSans**, com pesos 700/400 e stretch 100%. Há capturas clara/escura, acentos, sinais, números tabulares, valores reais e fallback. A 4.3 mantém Barlow como escolha de implementação; Plex é alternativa de comparação, não uma identificação histórica. Inter não foi acrescentada: as duas famílias normais existentes permitiram a prova solicitada sem novos arquivos.

## Iteração no navegador

1. Primeira leitura desktop/mobile confirmou o gráfico, contagens e ressalva do modelo na primeira tela de 390×844. Capturas intermediárias `round1-*` preservadas apenas localmente, conforme a política de evidências; as finais são versionadas. Aguardas de fontes e dois frames após resize evitam capturas com tiles antigos do compositor.
2. Inspeção de 200% encontrou sobreposição dos controles de lado da bola e Alterar recorte. O layout estreito passou a dar uma linha própria para cada conjunto e para a ação. A contraprova agora verifica também a ausência de sobreposição, além de overflow.
3. Comparação dos três temas levou às proporções próprias por identidade. Em 320 px o escudo BAL precisava de mais respiro; sua caixa agora limita a escala óptica pela largura disponível. Nova captura confirmou o ativo integral. Acrescentado espaço entre número e unidade no volume.

## Capturas duráveis

| Evidência | Arquivos |
| --- | --- |
| Temas lado a lado | [identidades](evidence/themes-side-by-side.png), recortes individuais `theme-BAL/DAL/NE.png`; somente cabeçalhos, sem eixos de comparação de eficiência |
| Mesmo BAL antes/depois, sem rolar | 1440×900: [4.2](evidence/before-4.2-desktop.png), [4.3](evidence/bal-desktop.png); 390×844: [4.2](evidence/before-4.2-mobile.png), [4.3](evidence/bal-mobile.png) |
| Página completa | [BAL](evidence/bal-full.png) |
| Defesa real | [DAL W2 passe](evidence/dal-defense.png), [NE POST2025 passe](evidence/ne-defense.png); mobile correspondente no mesmo diretório |
| Fonte ausente real | [BAL W3](evidence/bal-no-source.png), [mobile](evidence/bal-no-source-mobile.png) |
| Volume e detalhes abertos | [volume + precisão](evidence/volume-precision-open.png), [página completa](evidence/volume-precision-full.png), [mobile](evidence/volume-open-mobile.png), [origem](evidence/origin-open.png) |
| Tipografia normal | [prova](evidence/type-proof.png), [fallback](evidence/type-fallback.png), fontes efetivas em [browser.json](evidence/browser.json) |
| Acessibilidade | [320 px](evidence/bal-320.png), [texto 200%](evidence/text-200-mobile.png), [foco](evidence/keyboard-focus.png), [reduced motion](evidence/reduced-motion.png) |
| Estados sintéticos | `denominator-zero`, `complete-empty`, `exact-zero`, `near-zero`, cada um com versão desktop/mobile em `evidence/` |

O “antes” renderiza o componente/CSS 4.2 preservados no mesmo shell do laboratório. Não é uma captura de um deployment histórico. Os recortes de BAL têm os mesmos IDs e números nos dois componentes.

## Verificação e limites das provas

- **151 testes frontend em 13 arquivos**, lint e build aprovados. Logs: [tests.txt](tests.txt), [lint.txt](lint.txt), [build.txt](build.txt). Cinco novos testes cobrem o componente 4.3 sobre as fixtures existentes: identidades/frações, ausência/base zero, sucesso zero sem parcela artificial, semântica defensiva e não zero mínimo. Os cinco `it.fails` legados permanecem identificados e inalterados.
- **48 documentos reais** retornaram por HTTP com IDs de observação/DTO iguais aos resumos do catálogo validado. Casos inspecionados: BAL 65/115 → 56,5% / EPA +0,223; DAL defesa passe W2 17/35 → 48,6% / +0,035; NE defesa passe POST 56/160 → 35,0% / −0,324. Não foi repetida a infraestrutura ETL/Java histórica.
- **Browser:** 320, 390, 768, 1024 e 1440 sem overflow horizontal; 200% com reflow e controles sem sobreposição; reduced motion sem animações; seleção por teclado mantém foco visível. Troca 4.3/4.2 preserva o ID e não busca novo documento; recarga preserva seleção. A suíte existente cobre transporte, sessão, validação e cancelamento; não se anuncia uma nova campanha de corridas/reinícios nesta rodada.
- **Fixtures no browser:** apenas interceptações temporárias rotuladas SYNTHETIC. Near-zero deriva em memória da fixture de zero, com soma/razão/membro coerentes em −0,000001 e denominador 1. Demonstra formatação −<0,001; não é documento real nem nova fonte validada. Rotas foram removidas e BAL real restaurado antes da prova tipográfica. Bundle e servidor não receberam fixtures.
- **Contraste calculado:** tinta/papel 11,55:1; secundária/papel 5,79:1; secundária/limites 5,18:1; controles 6,80:1; nomes BAL/DAL/NE 13,18/8,59/14,51:1; contexto 9,19:1. Textura, contagens e legenda também distinguem o gráfico. São medições locais dos tokens, não um certificado de equivalência com pixels de vídeo.
- **Isolamento público:** [production.txt](production.txt) comprova arquivos públicos idênticos sob flags VITE adversas. O build final conserva JS `73f18e…f959ad5` e CSS `2b4ae1…344d41d`, iguais à base documentada. Nenhuma fonte, logo ou módulo da proposta entrou no bundle público.
- **Preservação:** [preservation.json](evidence/preservation.json) confere bytes de 4.2, formatador, cliente, modelo e guardas contra a base, registra hashes dos insumos/referências/fontes e ausência de diff nas árvores protegidas. Não foram alterados contratos, ETL, Java, Supabase, snapshots públicos ou pins.
- **Revisão React:** cálculo derivado no render, sem novo fetch/efeito por proposta; estado local apenas para falha do logo; keys de membros estáveis; formatadores/BigInt compartilhados; controles semânticos e foco preservados. Skills aplicadas: frontend-design, UI/UX Pro Max e react-best-practices. Nenhuma delegação ou mensagem a terceiros.

Reprodução das provas:

```bash
PLAYWRIGHT_MODULE='/Users/pedrocollet/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright' \
node docs/plans/metrics/e5c-4.3/verify-browser.cjs
/Users/pedrocollet/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 \
  docs/plans/metrics/e5c-4.3/verify-preservation.py
npm --prefix web-ui test
npm --prefix web-ui run lint
npm --prefix web-ui run build
python3 docs/plans/metrics/e5c-3/verify_production.py
```

A inspeção foi feita pelo agente, sem participantes humanos. Não comprova compreensão, qualidade editorial, atualização corrente, comparação certificada ou elegibilidade pregame. Capacetes/retratos seguem como evolução de ativos. Nenhum Gemini, banco, aquisição, instalação/execução de modelo, merge em main, push ou deploy foi realizado.
