# Reconferência e inspeção da entrega 2/5

## Evidência numérica

Pacote real validado pelo reader existente e pin exato; reconciliação da entrega 1 preservada. O verificador documental `verify_numbers.py` usa `Fraction`/`Decimal`, independente do formatador TypeScript. A interface mantém somas decimais como strings; só a geometria usa razão quantizada antes de converter para Number.

| EPA por jogada válida | NYJ | Denominador NYJ | TEN | Denominador TEN |
| --- | ---: | ---: | ---: | ---: |
| Geral | +0,168 | 60 | −0,119 | 49 |
| Passe, incluindo sacks | +0,406 | 24 | −0,210 | 35 |
| Corrida, incluindo scrambles | +0,010 | 36 | +0,110 | 14 |

As seis renderizações foram reconferidas no teste e navegador. Zero é explícito no eixo comum aos dois ataques; denominador próprio sempre acompanha o valor. Não se aplica elegibilidade de terceiras/red zone ao EPA. O modelo permanece UNKNOWN; não há benchmark EPA da liga.

| Família | NYJ | TEN | Referência W1 |
| --- | --- | --- | --- |
| Terceiras elegíveis | 2/10 (20,0%) | 4/12 (33,3%) | 32 pontos ofensivos; conjunta 154/377 (40,8%) |
| Terceiras 7+ | 1/5 (20,0%) | 1/5 (20,0%) | Sem referência adicional |
| TD / campanhas de red zone | 2/3 (66,7%); 2 TD, 1 FG | 1/1 (100,0%); 1 TD | 31 pontos; conjunta 70/108 (64,8%) |

São **22 marcas reais de terceira**, com IDs originais e vínculo distância × tipo × conversão, e **quatro campanhas**, em ordem da fonte, com evidências de entrada/desfecho. Não se reconstruíram cruzamentos por marginais nem se contaram entradas como oportunidades extras. Os testes confrontam cada ID renderizado e a partição conjunta com as unidades, preservando a igualdade ataque/defesa já auditada no pacote. A defesa adversária é contexto da mesma amostra.

ATL aparece no inventário como fonte presente, 0/0 e sem taxa de red zone; fica fora da distribuição. Taxa conjunta usa somas dos numeradores/denominadores; não é média ou mediana de taxas. NYJ/TEN pertencem à referência, explicitamente não independente. Pontos compartilham eixo 0–100%; sobreposições mudam apenas de faixa vertical. BUF/TEN/WAS com 4/12, por exemplo, mantêm a mesma posição horizontal. Razões estão disponíveis por foco/toque e lista textual.

O calendário existente confirmou `2026_01_NYJ_TEN`, NYJ visitante/TEN mandante, 13/09/2026, placar **23 × 10**, trio atômico `awayScore=23`, `homeScore=10`, `result=-13`. Os testes incluem identidade incompatível e placar ausente. Resultado ausente não é fabricado.

## Inspeção real no navegador

A referência anterior foi observada em 18100 antes da implementação. Capturas finais e registro em [evidence/](evidence/browser.json). Desktop 1440 e mobile 390/320: sem rolagem horizontal da página, 22/4 marcas e 32/31 pontos em todos os tamanhos. Fonte 200% em 320, corpo computado 32px: leitura e detalhes preservados, sem reduzir fontes; tabela de auditoria tem rolagem própria. Fonte e viewport temporários foram restaurados.

Verificados teclado/foco visível, Tab/Enter no EPA, tentativas e campanhas com IDs, lista/pontos da liga, regras e auditoria, links de resumo/âncoras, recarga no link direto, retorno ao explorador e histórico do navegador. A alternância EPA mantém os dois ataques e não altera as outras unidades. Nenhum erro de console na aba final.

Falha de fonte simulada somente na aba de teste por bloqueio da requisição: página exibe indisponibilidade contextual, sem valores EPA, tentativas ou campanhas substitutas. Bloqueio removido e fonte real restaurada. Não se alteraram pacote/configuração ativos para simular falha.

Ajustes após inspeção:

- Pontos/eixo SVG inicialmente pequenos no mobile deram lugar a pontos HTML de tamanho fixo e lista com alvos de 44px. Empilhamento vertical mantém o valor real no eixo.
- Abertura, navegação e frase de contexto ficaram mais compactas; identidade transparente e painel contínuo foram mantidos.
- Detalhes de campanha e regra ganharam texto equivalente explícito, sem depender de hover/cor. Auditoria técnica permanece recolhida.
- Mercado identifica campos brutos; removidos termos de implementação da mensagem principal de erro. Nenhuma interpretação de spread foi acrescentada.

As capturas ampliadas usam clip em coordenadas CSS para evitar recorte incorreto do protocolo em tela Retina. Elas registram inspeção pelo agente, **não um estudo com pessoas**.

## Testes e isolamento

- **293 testes frontend, 29 arquivos**, incluindo 12 novos; grupo real executado com o pacote. Cinco `it.fails` legados permanecem inalterados.
- Lint limpo, TypeScript das entradas journey e matchup aprovados, cinco builds aprovados: matchup, journey, real, experience e público. Logs finais em `checks/`.
- Casos sintéticos só em teste: ausência, insuficiência, zero oportunidades versus zero válido, operação recusada, pin divergente, período/participantes/unidades incompatíveis. Não entram na aplicação.
- HTTP: 15 requisições reais (duas respostas integrais, 13 recusas) e duas rejeições de startup pelo adapter/reader (pin incorreto/fonte ausente). Resposta idêntica aos 243.841 bytes do artefato; sem fallback.
- **2.169 arquivos históricos preservados byte a byte**. Duas adições explícitas em arquivos históricos: bootstrap lazy do piloto e ignore do build privado. App, explorador, estilos/configurações/fontes/contratos antigos e processamento Python intactos.
- 192 documentos situacionais idênticos entre consumidores; catálogo antigo igual e 24 respostas NYJ/TEN W1 e W1–2 idênticas; resposta foundation igual em 18101/18102. Fontes e cópia de recuperação conferidas contra inventários da entrega 1.
- Na conferência anterior à retomada, listeners 18098/49375, 18099/64333, 18100/74464, 18101/95101 e 18102/97976 estavam ativos. Na retomada de 24/10, os três primeiros estavam ausentes e as portas livres; foram restaurados pelas mesmas configurações e worktrees limpas. PIDs atuais: 18098/30244, 18099/30251, 18100/30265; 18101/95101 e próprio 18102/97976 continuaram ativos. As mesmas respostas foram reconferidas após restaurar; recibo e hashes dos commits estão em `checks/restored-references.json`. Nenhum processo foi encerrado para liberar porta. Referência original permanece limpa no HEAD exigido.

Hashes SHA-256 do build público, iguais à base:

| Ativo | SHA-256 |
| --- | --- |
| JS | `73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5` |
| CSS | `2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d` |

Não se repetiram testes Java/banco nem pipeline Python: nenhum processamento correspondente foi alterado. O reader Python completo foi executado no startup e nos checks de transporte/integridade. Sem novas dependências, ativos, frameworks ou chamadas a Gemini/motor local.

## Limites preservados e decisões para a próxima entrega

A página descreve somente registros observados desta partida, com autorização concreta por operação. Disponibilidade da observação não concede comparação genérica. Facts exigem evidências exatas e permissão de diferença; display, sideBySide e leagueReference também são verificados. Estados AVAILABLE, NO_OPPORTUNITIES, INSUFFICIENT e SOURCE_ABSENT conservam significados distintos na apresentação, sem expor rótulos técnicos ao leitor.

Completude, disponibilidade histórica, modelo EPA e demais garantias UNKNOWN continuam desconhecidos. Não há inferência causal do placar, capacidade estável, significância, ranking certificado ou prognóstico. TEN 100% é inseparável de 1/1, enquanto NYJ tem maior contagem de TDs. Os três fatos vêm do pacote, sem geração editorial automática.

W1 não tem semanas regulares anteriores neste recorte; isso é motivo de domínio. W2 e agregado W1–2 não entram no piloto. Não se afirma conhecimento pré-jogo. Cotações são registros brutos de schedule com fornecedor/captura UNKNOWN: não são linha pré-jogo ou fechamento, nem sustentam favorito, confiança, edge ou recomendação. Mercado separado da análise tática.

A entrega 3/5 pode avaliar compreensão dos denominadores, período e taxa versus contagem, usando o roteiro preparado. Nenhuma conclusão sobre compreensão humana é afirmada nesta entrega.
