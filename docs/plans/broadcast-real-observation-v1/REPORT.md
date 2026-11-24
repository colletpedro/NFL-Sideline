# Leitura real individual · relatório de 21/10/2026

A cadeia **bundle completo → reader/adapter Python aceito → sessão congelada →
HTTP real → interface** foi demonstrada nesta worktree. São 48 documentos do
catálogo nominal REAL_ARCHIVE: 42 com fonte e seis recortes BAL W3 sem fonte.
A entrega é local. A referência de duas equipes, o laboratório anterior e o site
público permanecem separados.

## Base, configuração e preservação

- Base exata: `b59a8deb60aec318a6ed984a55b87a993b44b14d`, conferida na referência
  `codex/broadcast-axis-baseline-v4`, limpa e preservada.
- Worktree gerenciada: `/Users/pedrocollet/.codex/worktrees/broadcast-real-observation-v1/NFL Sideline`.
  Branch: `codex/broadcast-real-observation-v1`.
- Commit de implementação: `cc0ad2a42ee0df2e4035675ab70e7824236e22e8`.
  O commit documental seguinte reúne estas evidências. HEAD final é obtido por
  `git rev-parse HEAD` e informado na entrega; não há hash autorreferente no relatório.
- Checkout original conservou HEAD `98cca81929f740cd026737a3acb2d8d625fcecae`.
  Nenhuma alteração dos arquivos de dados, contratos, writer, schema/migrations,
  seleção temporal, aprovações, snapshots públicos, workflow ou Production.
- [Configuração nominal](lab-config.json), cópia dos mesmos bytes da configuração
  E5c-3R; somente uma entrada REAL_ARCHIVE, com path principal e pin aceito.
- Python existente no checkout original, dependências Node existentes por symlink.
  Não houve instalação, aquisição, backfill, `.env`, SQL/banco, Docker ou Gemini.

A CLI pública validou o principal e conferiu o pin antes de qualquer edição de
interface; o resultado foi comunicado nesse momento. [preflight.json](preflight.json)
registra a repetição auditável e acrescenta a leitura da cópia completa de backup. Nenhuma restauração foi
necessária. O reader rederivou as observações a partir dos originais autocontidos;
`review-observations.json` nunca foi entrada operacional ou fonte dos números.

## Identidades e reconciliação

| Identidade | Valor preservado |
|---|---|
| Bundle | `sha256:2fae3be2b1ab7e5799287469ec29b9a98ff652a365ccafcb11b46c55d98ace8a` |
| Sessão congelada | `sha256:a0b4a5b4ffbac39ef3ea827c1c7b0b53a30156aa1a94214da3722630dd3d9e2c` |
| Materialização | `sha256:f7a70f61b442d8d631e858ac05c5c6191652b8d0ed0ffd5a7ac8094939a8d3fa` |
| Input temporal | `sha256:9dc7e6de11af1d0e494877c82f6cc234be3cbe002ab5ee47bf29cc2cf1d3a0e6` |

[http.json](http.json) enumera observationId/dtoId/contexto de todos os 48 documentos,
com hashes relativos do bundle antes/depois. Todos os READY foram reconciliados com
a projeção do reader, sem tolerância float. O ensaio soma contagens inteiras e somas
EPA por Fraction sobre membros da mesma observação; confere volume eligibleN/1,
EPA epaSum/epaN, sucesso successN/epaN e frequência eligibleN/generalEligibleN apenas
para passe/corrida. Não soma observações sobrepostas. As cópias principal e backup
conservaram todos os bytes e produziram documentos/manifestos iguais.

O catálogo efetivo confere a coorte esperada: BAL/DAL 2026 REG W1, W2, W1–2;
NE 2025 POST W19–22; BAL 2026 W3 ausente. Cada combinação tem ataque/defesa ×
geral/passe/corrida. A escolha operacional vem somente desse catálogo validado.

[Exemplos capturados do próprio HTTP](examples.json):

| Caso | EPA médio da fonte | EPA positivo | Volume / frequência |
|---|---|---|---|
| BAL ataque geral W1–2 | `25.678661890850767072 / 115` → **+0,223** | `65 / 115` → **56,5%**; complemento `50 / 115` | **115**; geral sem frequência |
| DAL defesa contra passe W2 | permitido `1.212177313656378383 / 35` → **+0,035** | permitido `17 / 35` → **48,6%**; complemento `18 / 35` | **35**; `35 / 67` → **52,2%** |
| NE defesa contra corrida POST2025 | permitido `-14.04843875073169981 / 100` → **−0,140** | permitido `33 / 100` → **33,0%** | **100**; `100 / 260` → **38,5%** |
| BAL W3 sem fonte | desconhecido | desconhecido | desconhecido; nenhuma barra zero |

O período solicitado é separado das semanas efetivamente observadas e dos jogos
com fonte. Os quatro jogos de NE não significam cobertura de 100%. CURRENT é
origem declarada do pedido; não aparece como dado ao vivo, desta semana ou atual.

## Apresentação e diferenças para a demonstração

A referência foi lida integralmente e suas nove capturas foram abertas. A nova
composição conserva cenário ardósia, cores e logos locais, Archivo/Roboto Condensed,
painel claro contínuo, tinta escura, foco visível e hierarquia editorial.

O cartaz de duas metades virou uma faixa de time único com papel/fundamento e
período. Não há metade vazia, adversário inventado, placar ou resumo fictício. A
síntese é uma frase factual gerada pelas contagens da seleção. EPA aparece assinado;
a proporção de EPA positivo possui percentual, numerador/denominador e complemento
“EPA zero ou negativo”. “Explorar composição” abre contagens e exclusões do mesmo
recorte. Volume por jogo é uma lista literal dos membros, sem inferência de ritmo.

Reuso restrito ao necessário:

- `broadcast-experience/TeamLogo.tsx`: extração do Logo visual, também usado pela
  demonstração. Não importa fixtures ou regras editoriais.
- `broadcast-experience/experience.css`: identidade/tipografia existentes; a entrada
  real acrescenta regras locais para um assunto e corrige somente o nowrap registrado.
- `ObservationInspection`: detalhes existentes de contagens, membros, garantias,
  razões, escopos e identidades; recebe o mesmo DTO validado.
- `client.ts`, `model.ts`, `selection.ts`, `format.ts` e rótulos/período existentes:
  transporte, identidades, seleção nominal e formatação exata reutilizados.
- `broadcast-real/adapter.ts`: fronteira explícita de um DTO para apresentação.
  Preserva o DTO e suas garantias/limitações, calcula complemento por BigInt e usa
  HALF_UP exato. Geometria inteira limitada a 0..100%, sem alterar texto/sinal.
  Zero próximo do arredondamento conserva `+<`, `−<` ou `<`, conforme o formatter.

Não se importam fixtures da experiência, readSlice, seus limiares ou métricas de
jardas, terceiros downs e red zone. O bundle JS real também foi inspecionado para
impedir entrada da lógica fictícia. Não foi criada biblioteca genérica.

As seleções persistem na URL e em preferência própria. Controles permanecem
operáveis durante carregamento; AbortController, guarda de atividade e conferência
de sessão/entryId/observationId impedem resposta atrasada e mistura de rótulo/número.
Escolha removida ou arquivo inválido não gera fallback. Troca de time que exige
outro período é anunciada explicitamente.

## Limitações reais que permanecem

Integridade **RECONCILED** e compatibilidade básica **KNOWN** não promovem as demais
garantias. Nas 48 observações, completude, cobertura esperada e conhecimento temporal
são **UNKNOWN**; o modelo EPA também é **UNKNOWN**. expectedCount e coverageRatio
permanecem null. Nenhum score de confiança ou selo de dados completos foi criado.

“Modelo EPA não identificado” acompanha o valor EPA e o gráfico dependente de EPA.
Completude não confirmada, cobertura esperada desconhecida e conhecimento anterior
ao jogo não demonstrado permanecem visíveis fora dos detalhes. Nos detalhes ficam
todos os reasonCodes, limitations e fieldScopes originais. unknownFilterFlagsN é
contexto do jogo, sem estatística de fundamento ou soma entre observações.

REAL_ARCHIVE é a declaração nominal do operador; o reader verifica a cadeia
aceita, sem autenticar terceiros. A reconstrução atual não demonstra conhecimento
histórico. Não há ranking, diferença entre documentos, superioridade, vantagem
certificada, previsão, vencedor ou permissão pregame. Esta entrega não é pesquisa
com participantes nem nova aprovação editorial/visual humana.

## Transporte local

Porta própria **127.0.0.1:18090**, com env explícita no [comando de startup](README.md).
A única alteração no transporte aceito é o parâmetro validado de porta loopback,
com default 18083 preservado. O mesmo parâmetro liga Vite a Host/Origin exatos.
Métodos, rotas, marcador, corpo, sessão e demais recusas conservam a semântica.
Sem CORS curinga, proxy de geração, bind externo ou protocolo novo.

HTTP real: 48 respostas idênticas ao DTO do reader, catálogo/session/pin conferidos,
no-store/nosniff e **16 contraprovas**: Host/Origin de outra porta ou domínio,
localhost em vez do IP literal, marcador inválido, POST/HEAD/OPTIONS, corpo, query,
travessia/encoding, sessão ausente/divergente e documento inexistente. Resultados:
403, 409 ou 404 conforme contrato; a origem correta funciona. Os testes existentes
também continuam cobrindo os demais métodos/rotas/identidades.

Startup valida/congela uma vez. Os cliques do navegador emitiram somente GETs de
mesma origem; nenhuma execução de geração foi acionada. Reinício com bytes iguais
pode conservar o sessionId. Esta entrega não anuncia mudança de identidade por PID.

## Navegador, reflow e estados

[Chrome próprio 155.0.8059.85](evidence/browser.json), encerrado em finally:
48 documentos reais percorridos, números confrontados com cálculo BigInt
independente no teste, frações exatas e todas as limitações abertas e conferidas.
Ataque/defesa e os três fundamentos, múltiplos jogos, POST separado e W3 ausente
estão nas capturas reais listadas no [README](README.md).

24 medições: 1440/900/390/320 × texto 100%/200% × leitura disponível/detalhes e
seleção abertos/ausência. Em todos, scrollWidth coincide com viewport. Nenhum
corte ou redução de fontes foi usado. EPA, percentual e contagem principal também
foram conferidos em uma linha inteira. A grade passa a uma coluna quando necessário.

Teclado: skip link, foco visível, select sem perda de foco, gráfico por Enter,
detalhes por Enter/Space. Recarga preserva a escolha. O ensaio de atraso força fetch
a ignorar abort para verificar também a guarda de atividade/identidade; a resposta
antiga não substitui a nova, e nenhum número antigo permanece durante loading.
Falha de rede e 409 produzem mensagem e recuperação explícita, sem observação visível.

Fonte ausente, fonte presente vazia, COMPLETE vazio, zero conhecido, denominador
zero, EPA ausente/não finito e números não representáveis por Number são separados
nos testes de adaptador/apresentação. Estados sem ocorrência real usam a sessão
sintética preexistente exclusivamente nos testes; não entram em REAL_ARCHIVE.

[Reflow da referência](evidence/reflow-reference.json): em 320 px/root 32 px, o
`stats-title p` anterior tinha nowrap, fonte 26 px, altura 39 px e página **362 px**.
A regra corrigida usa reflow, mesma fonte 26 px, altura 78 px e página **320 px**.
O gráfico EPA continua com rolagem local **260/512 px**, avaliada separadamente.
A referência anterior foi apenas lida no seu servidor 18089. A correção foi testada
em servidor próprio temporário 18091, encerrado em finally.

A inspeção visual também levou a reflow das chaves longas de proveniência e a
ajustes da grade para impedir quebra de tokens numéricos. Nenhum texto foi ocultado.

## Checks e encerramento

[Resultados e logs](checks/results.json): **179 testes frontend**, incluindo os
12 novos testes de adaptador/apresentação e as cinco falhas esperadas legadas,
preservadas byte a byte. Lint, build público, build da experiência, build real e
git diff --check aprovados. Revalidação real completa e prova HTTP aprovadas.
Nenhuma suíte Java ou ETL completa foi executada, pois seus componentes não mudaram.

[Isolamento desta entrega](isolation.json) compara a base exata e só autoriza a
adaptação de porta no middleware e o novo script de startup dentro das áreas
protegidas. JS/CSS públicos conservam SHA-256:
`73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5` /
`2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d`.

O verificador histórico da demonstração foi executado e conservado sem edição.
Ele recusa a mudança de observations.ts por proibir qualquer alteração em build/;
essa recusa é esperada para a exceção explicitamente autorizada nesta entrega.
O novo check não altera seu baseline nem reivindica que ele passou.

Revisão React realizada com `vercel:react-best-practices`: cancelamento e identidade,
efeitos com dependências explícitas, controles nativos rotulados, foco e sem imports
amplos de dados fictícios. Skills frontend-design/ui-ux-pro-max orientaram preservação
da referência e checks de reflow; nenhum deles mudou contratos ou exigiu aprovação.

Servidor real deixado ativo: **PID 21282**, somente 127.0.0.1:18090.
Encerrar apenas o próprio: `kill -TERM 21282`. Servidores anteriores continuam nos
PIDs 69029/770/4041/15045, portas 18086/18087/18088/18089. O temporário 18091 está
fechado. Sem merge, push ou deploy. HEAD final e estado limpo constam da entrega.
