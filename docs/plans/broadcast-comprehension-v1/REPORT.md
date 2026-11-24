# Relatório final · entrega 3/5

**Encerrada no escopo revisado pelo usuário: N=1 humano, coleta encerrada, análise qualitativa individual. Recomendação: avançar para 4/5 com os limites abaixo.** A [emenda posterior à coleta](AMENDMENT-01.md) não reescreve o protocolo original; os limiares 4/4, 4/5 e 80% não foram aplicados. Não se calcularam percentuais de sucesso ou incidência entre usuários.

## Verificação técnica

Base da preparação limpa no HEAD esperado `68eaf4179de72c6accc56749f9d4565666a23536`. Continuidade na mesma worktree/branch, sem modificar a referência limpa 18102 em `c5be5b0dbb525faea85fab350039d8a5c1c87af5`. Uma linha do código de aplicação substituída, exclusivamente o primeiro parágrafo de unidade de EPA; demais arquivos históricos fora da documentação de pesquisa (**2.220**) iguais à base. Protocolo original intacto.

A instância própria usa 18103, loopback/strictPort, PID 44780, configurações explícitas do operador e o reader/pin existentes no startup. Os adaptadores já parametrizados recebem a porta coerentemente; não houve relaxamento de Host/Origin ou alterações de contrato/configuração antiga. [Operação e comandos](README.md).

Checks realmente executados, [logs em checks/closure/](checks/closure/isolation.json):

- 12 testes específicos do piloto com pacote real e seis regressões legadas: **18 passaram**; as cinco falhas esperadas (`it.fails`) preservadas.
- Lint, TypeScript da configuração experimental e **cinco builds**: journey, matchup, real, experience e público aprovados.
- Dez requisições de conferência: três respostas integrais (referência e nova, inclusive Origin correto) e sete recusas (método, Origin externo/18102, Host de 18102, query/caminho, marcador, corpo). Resposta de ambos os servidores idêntica aos **243.841 bytes** do artefato e pin esperado.
- Preservação dos cinco listeners anteriores nos mesmos PIDs; nova porta não substituiu nenhuma referência.
- Geral/Passe/Corrida em 1440, 390 e 320 px (nove combinações), mantendo seis valores/denominadores, domínios comuns, 22 tentativas e quatro campanhas. Uma explicação por bloco, sem cortes, sobreposição ou rolagem horizontal da página. Capturas inspecionadas.
- Teclado Tab/Enter, foco visível e abertura da regra; regra preserva população própria e modelo não identificado. Texto a 200% em 320, corpo computado 32px: quebra de linhas e rolagem vertical normais, sem sobreposição/corte horizontal. Fonte e emulação restauradas; nenhum erro de console na aba refinada.

Hashes públicos SHA-256 iguais à base: JS `73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5`; CSS `2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d`. Fontes, snapshots, cálculos, unidades, permissões e disponibilidade preservados. Nenhum teste novo espelha a frase. Não foram repetidos Java/banco, pipeline ou reconciliação histórica dos registros brutos: não houve mudança correspondente.

## Coleta humana realizada

**Uma sessão humana recebida: P01**, data informada 24/10/2026. O registro completo anteriormente chamado SIM01 foi encontrado em `/Users/pedrocollet/Downloads/NFL Sideline/docs/plans/broadcast-comprehension-v1/coleta-2026-10-24/simulacao/SIM01.md`; cópias físicas com SHA-256 preservam a procedência. Sua classificação anterior foi corrigida pelo esclarecimento expresso do usuário. Registro canônico [P01](results/P01.md), respostas como **paráfrases revisadas**, nunca transcrições literais.

Perfil informado: NFL semanal/melhores momentos; ouviu falar de EPA, não usa; outras estatísticas avançadas básicas; primeira visita no cenário avaliado. Computador/navegador integrado em painel 532 × 827 px, com automação de cliques descrita. Consentimento, confirmação de maioridade, tempos e condições não fornecidas permanecem não documentados. Autoria de cada ação não é inferida. Isso limita conclusões de navegação independente e não invalida a origem humana das respostas informada pelo usuário.

A preparação inicialmente tinha zero sessões. Depois houve o registro, o esclarecimento e a correção para P01. A coleta foi **encerrada por decisão do usuário**, sem recrutar mais pessoas. Walkthroughs/capturas do agente são verificações técnicas, não sessões adicionais.

## Interpretação dos resultados

| Evidência de P01 | Interpretação qualitativa | Limite |
| --- | --- | --- |
| T1: TEN 4/12 e 33,3%, NYJ 2/10 e 20%, neste jogo; resumo e Terceiras | Comparação geral respondida | Exploração por distância e compreensão das marcas não demonstradas; não é falha automática |
| T2: Jets × Titans, W1 de 2026, cabeçalho/data/“deste jogo” | Período identificado | Conferência DOM não comprova rolagem humana ao topo |
| T3 espontâneo: NYJ mais TDs, TEN maior taxa; após complemento: 1 TD/1 campanha e sem estabilidade | Taxa e contagem distinguidas; limite da amostra explicitado após a pergunta | Não atribuir estabilidade ao espontâneo; marcas independentes não avaliadas |
| T4: sinais, quatro valores relatados de Geral/Passe e denominadores; unidade ainda pouco compreendida | Compreensão parcial de EPA; acesso ao passe relatado | Divergência checkbox/botão pertence à automação, não a dificuldade humana |
| T5: ataque/time W1 e comparação descritiva; NYJ pela lista | Contexto entendido; lista é caminho legítimo | Identificação direta de NYJ/TEN nos pontos não avaliada |
| T6: Método e procedência, menção a marca | Caminho pertinente encontrado | Marcas individuais não consultadas na tarefa |

Observação, ações descritas, verificação mecânica, interpretação e não observado permanecem separados em P01. Não há evidência para estimar frequência em outras pessoas ou certificar navegação sem apoio. A dúvida conceitual de EPA é a evidência específica para o acabamento; H2 (identificação direta dos times) e H3 (extensão mobile) continuam sem avaliação humana suficiente para mudar a interface.

## Refinamentos implementados

Somente o parágrafo visível junto do gráfico EPA foi substituído, nos três fundamentos:

- Antes: “EPA · pontos esperados por jogada com EPA válido · deste jogo”.
- Depois: “EPA/jogada é a variação média dos pontos esperados nas jogadas com EPA válido deste jogo. Positivo indica ganho; negativo, perda. Não é o placar.”

Compatibilidade conferida com `classified-scrimmage-v1`, definição/adapter 1.0.0 e [política da base](../broadcast-comparison-foundation-v1/POLICY.md): numerador soma decimal da coluna EPA, denominador EPA finito na população própria. Não foram alterados valores ou aplicado filtro situacional ao EPA. O texto informa média e sinais; não interpreta o modelo UNKNOWN como identificado/certificado.

A substituição evita um parágrafo adicional. Detalhe de sacks/scrambles, mesma escala, denominadores visíveis e regra com modelo não identificado permanecem. Não houve novo controle, tooltip obrigatório, exemplo numérico, fato, redesenho de marcas/pontos ou reorganização da página. [Antes/depois e capturas mobile](README.md#antes-e-depois-de-epa).

## Reconfirmação humana

**Não realizada.** O esclarecimento foi implementado em resposta ao relato de P01. Não se afirma resolução da dificuldade. Testes, cliques e imagens do agente demonstram funcionamento/renderização, não compreensão humana da nova frase. Não se exige nova rodada para encerrar o escopo revisado.

## Pendências, limites e decisão

A 3/5 está encerrada no escopo revisado. Permanecem não avaliados: compreensão independente das marcas, identificação direta dos times no gráfico, uso em celular físico e frequência desses comportamentos em outras pessoas. Condições não informadas, automação e revisão posterior das respostas acompanham a passagem. Modelo EPA, completude e disponibilidade histórica continuam UNKNOWN; não há prognóstico, causalidade do placar ou benchmark EPA da liga.

Recomendação: **avançar para 4/5**, para aplicar a estrutura aos demais confrontos W1–2 mantendo definições, denominadores, permissões e limites de cada fonte. O pacote atual continua sendo do piloto; não autoriza preencher outros confrontos com seus dados. [Passagem documentada](HANDOFF-4-OF-5.md). A 4/5 não foi implementada. Sem merge, push, deploy ou publicação.
