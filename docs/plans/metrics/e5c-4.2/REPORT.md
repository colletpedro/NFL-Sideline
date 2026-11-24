# E5c-4.2 — fundação visual de transmissão

Uma nova mesa de análise clara, sobre cenário escuro discreto, substitui a apresentação do piloto: identidade cromática do clube, logo ancorado, tipografia Barlow local, contexto ardósia e gráfico único de composição. EPA e amostra apoiam a observação. No mobile, gráfico e denominador aparecem na primeira tela; ressalva do modelo vem antes dos números secundários.

## Experimentar

http://127.0.0.1:18083/ → **Transmissão 4.2**. **Versões anteriores** preserva A/B/C e E5c-4; mudar proposta mantém o recorte. Prova das duas famílias: http://127.0.0.1:18083/broadcast/type-proof.html . Sessão nova inicia em BAL ataque geral W1–2; seleção válida existente é restaurada.

```bash
cd '/Users/pedrocollet/.codex/worktrees/visual-reading-e5c4/NFL Sideline'
NFL_OBSERVATION_CONFIG='/Users/pedrocollet/Downloads/NFL Sideline/docs/plans/metrics/e5c-3r/lab-config.json' \
NFL_OBSERVATION_PYTHON='/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' \
npm --prefix web-ui run editorial:dev
```

Servidor próprio mantido para experimentação. Ctrl+C no terminal que o iniciou encerra-o. Não exige banco, aquisição, Gemini ou modelo local.

## Decisões e referências

As 12 imagens integrais do pacote `docs/plans/visual-broadcast/2026-10-20/` do checkout original foram abertas visualmente. 01–05 orientaram cabeçalho cromático, faixa ardósia, superfície clara e alinhamento; 02/04 foram as referências principais de organização. 06–12 orientaram profundidade, respiro e ancoragem da identidade; 10 também sustentou o tema prata/navy dos Cowboys. Não copiamos assinaturas ESPN, retratos ou recortes das capturas. Pacote original preservado, sem integração indiscriminada de seu checkout.

`DESIGN.md` registra o esboço anterior à implementação. `ASSETS.md` traz escolha tipográfica, fontes reais, versões/licenças, temas e inventário inicial. Barlow é a recomendação de implementação; a prova Plex permanece acessível. A decisão final de design continua com o usuário.

Trade-offs: painel estável e legível ocupa o centro, com cenário periférico discreto. Uma barra proporcional substitui as duas faixas grandes da B. Contexto indispensável continua visível, mesmo acrescentando altura. Capacetes não foram incluídos sem ativo adequado; logo resolve a identidade. A prova tipográfica é página própria para não carregar a exploração esportiva com controles de design.

## Gráfico e campos

| Representação | Pergunta e fonte | Denominador / limite / alternativa |
| --- | --- | --- |
| Composição principal | Quantas jogadas com EPA tiveram valor positivo? `totals.successN`, `totals.epaN`, `values.successRate` | Base EPA, não automaticamente toda a amostra. Complemento `epaN-successN` com BigInt inclui zero **ou** negativo. Área usa formatador proporcional exato compartilhado; texto da figura contém contagens e taxa. Sem células que aparentem jogadas individuais. |
| EPA de apoio | Qual a mudança média nos pontos esperados? `values.epa`, `presentation.epaDecimals` | `totals.epaN` ao lado; sinal e precisão aceitos, referência explícita ao zero. Não vira score. |
| Frequência, quando aplicável | Quanto o fundamento ocupa da população classificada? `values.frequency`, `eligibleN/generalEligibleN` | Texto secundário, distribuição e não qualidade; não renomeia o complemento como outro fundamento. |
| Volume por jogo, expansível | Quais volumes constam dos membros? `members` via componente aceito | Contagens individuais, lacunas separadas, sem tendência ou eficiência. |

BAL validado: 65/115 → 56,5%; EPA +0,223; 115 observadas. DAL defesa/passe W2: 17/35 → 48,6%; EPA +0,035. NE defesa/passe POST2025: 56/160 → 35,0%; EPA −0,324. Valores vêm do documento validado. Defesa identifica valores permitidos ao ataque adversário. W3 sem fonte não produz percentual ou contagem zero de jogadas.

## Três rodadas de refinamento

1. **Tipografia/composição:** comparadas Barlow e Plex em painel claro/escuro; confirmadas faces reais. Primeira tela revelou logo cortado por altura percentual, rótulos herdando cinza inadequado e controles altos no mobile. Corrigidos caixa explícita, escala óptica, tinta dos rótulos, alinhamento e organização dos controles. Evidências `round1-*` e prova.
2. **Gráfico/temas/mobile:** conferidos BAL, DAL, NE e ausência de fonte. Reduzida escala da estrela DAL para respiro; removida frase redundante no ataque; ressalva do modelo movida para junto do gráfico mobile. 320, 390 e 1024 sem overflow; sem comprimir letras ou encolher indiscriminadamente. Evidências `round2-*` e telas finais.
3. **Acabamento/estados/acessibilidade:** taxa exatamente zero não desenha nem borda de parcela positiva; vazios e controles durante carregamento receberam contraste próprio. Teste por teclado encontrou perda de foco após remontagem: restaurado apenas se a pessoa não navegou a outro elemento. Conferidos denominador zero, EPA mínimo, fonte pendente, fallback, texto 200%, reduced motion e sessão incompatível. Resposta antiga cancelada não substituiu a nova. Evidências de estados e JSONs.

## Capturas

| Caso | Evidência |
| --- | --- |
| BAL 1440×900 / 390×844 | [desktop](evidence/bal-desktop.jpg), [mobile](evidence/bal-mobile.jpg) |
| Página completa | [piloto](evidence/bal-full.jpg) |
| Mesmo BAL na B anterior | [comparação](evidence/previous-B-bal.jpg) |
| DAL / NE defesa | [DAL](evidence/dal-defense.jpg), [NE](evidence/ne-defense.jpg) |
| BAL sem fonte | [W3](evidence/bal-no-source.jpg) |
| Duas famílias | [prova completa](evidence/type-proof.jpg), [durante carregamento](evidence/type-loading.jpg), [fallback](evidence/type-fallback.jpg) |
| Estados e acessibilidade | demais capturas e auditorias em `evidence/` |

Dimensões são viewports solicitados; capturador pode normalizar pixels e retirar barra de rolagem. Evidências anteriores preservadas. Inspeção feita por agente, sem participantes humanos.

## Validação

- 146 testes frontend em 12 arquivos aprovados; lint e build: logs `tests.txt`, `lint.txt`, `build.txt`. Cinco `it.fails` legados preservados sem alteração ou reclassificação.
- `production.txt`: build público com flags VITE adversas tem os mesmos hashes JS/CSS da E5c-4.1. Nenhuma fonte, logo ou módulo local foi incorporado ao público.
- `real-documents.json`: catálogo e 48 documentos HTTP acessíveis, identidade conferida. Pins e seis hashes de arquivos do bundle conferidos sem alteração. Casos reais acima inspecionados no navegador e comparados aos documentos.
- `evidence/race.json`: requisição de passe retida, troca para corrida, resposta nova exibida; a antiga estava cancelada. Foco permaneceu em Corrida. Sessão 409 recusada com ação explícita de recarregar; recuperação real conferida.
- Seleção → documento → troca por teclado → precisão → recarga. Recorte mantido ao alternar B/4.2. Testes existentes de sessão, identidade, seleção e transporte reutilizados. Não foram repetidas suítes ETL/Java.
- Fixtures existentes servidas por interceptação temporária no navegador, sem modificar bundle ou servidor: EPA zero, base EPA zero e −<0,001. Todas as interceptações e emulações removidas; sessão real restaurada.
- Foco visível, alvos principais ≥44 px, alternativa textual e textura no gráfico. 320/1024 sem overflow e texto 200% com reflow. Reduced motion respeitado. Contraste em `contrast.json`. Fontes customizadas confirmadas por CDP.

## Pendências reais

Aceite visual do usuário e operacional do orquestrador pendentes. Nenhuma compreensão humana comprovada. Protocolo pronto: identificar time/papel/fundamento/período; explicar a barra e o denominador; localizar amostra e origem; mudar para defesa; diferenciar frequência de eficiência; explicar por que W3 não é zero e se a tela permite prever vencedor. Registrar falas e dificuldades reais, sem tempos ou taxas inventados.

Biblioteca completa de capacetes/retratos e autorização de publicação de ativos de marca são evolução própria. Registro hex usa fontes secundárias com derivação local explícita; não foi obtido manual oficial vigente dos três times. Dados continuam históricos e com UNKNOWN; não autorizam previsão, comparação certificada ou qualidade editorial presumida.

## Continuidade

Worktree e branch solicitadas preservadas. Base limpa `5bf78873cce0d1711c44f187744702af0b377aa4`; nenhuma divergência encontrada. Bundle `sha256:2fae3be2b1ab7e5799287469ec29b9a98ff652a365ccafcb11b46c55d98ace8a`. Implementação: `a31c1a5`. O commit documental seguinte preserva relatório, inventário e evidências; HEAD final informado na entrega. Sem merge, push, deploy ou publicação.
