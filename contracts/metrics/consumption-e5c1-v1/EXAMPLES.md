# Exemplos determinísticos e propriedades

Todos os documentos em examples.json são **SYNTHETIC**, inclusive história,
receipts e modelos. IDs sintéticos são sha256 de rótulos explicitamente sintéticos,
não hashes de bytes reais arquivados. As garantias aceitas são premissas do vetor;
validar schema não comprova essas premissas. Nenhum número de time real foi
recuperado de relatório resumido ou de PIT. decisions contém testemunhas mínimas
por operação; não dispara projeção/seleção/comparação de dados reais.

| Caso | Resultado esperado / motivo principal |
|---|---|
| reconciled_unknown | Ponto EPA 1/2 exibível, completude UNKNOWN; comparação EPA recusada |
| partial_sample | Volume/frequência amostrais comparáveis, subset PARTIAL explícito; eficiência/período/pregame recusados |
| absent_source | Todos valores null; lacuna distinta de zero e sem grupo |
| empty_unknown | Volume observado 0; EPA/SR/frequência null, completude desconhecida |
| empty_complete | Volume 0 com premissa sintética de completude; EPA/SR/frequência continuam null |
| valid_zero | EPA=0/2, SR=0/2 conhecidos; não missing |
| no_epa | B=2/E=0, volume2/frequência1/2 conhecidos; EPA null, NO_EPA_OBSERVATIONS |
| unknown_model | EPA exibível com modelo UNKNOWN; EPA/SR não alinháveis mesmo com fonte COMPLETE |
| incompatible_model | Dois modelos conhecidos diferentes: pontos preservados, volume/frequência comparáveis, EPA/SR recusados |
| incompatible_period | W1 versus W3: valores individuais preservados, todas comparações recusadas |
| incompatible_population | População diferente entre lados: só individuais; sem amostra comparável |
| expected_unknown | Expected/count/ratio null, número observado não gera taxa; volume amostral pode ser comparado |
| display_only | Flags desconhecidas: exibição literal reconciliada, nem amostra qualificada |
| descriptive_not_pregame | Fontes completas/modelo comum: EPA/SR descritivos elegíveis, tempo UNKNOWN recusa pregame |
| pregame_data_only | Premissas sintéticas completas no corte: T passa como dados; superioridade/time/teses continuam recusadas |
| completeness_conflict | Valores íntegros, declarações divergentes; período/eficiência/pregame recusados |
| temporal_conflict | Descrição completa pode passar; conflito temporal bloqueia T |

history contém contraprovas **sintéticas**: correção posterior ao corte, conflito
de declarações e recebimento atual versus disponibilidade antiga. Listas chosen,
rejected e motivos são golden expectations, não resultado de um seletor novo.
O verificador confere cronologia e preservação do escolhido, sem executar PIT.

Propriedades verificadas: normalizar ordem/réplicas idênticas do mesmo membro
não aumenta totals/identidade; mesmo gameId com conteúdo divergente é inválido;
alternativa inelegível fica fora do documento escolhido; falta de garantia não
vira zero/COMPLETE; recusa conserva documento/valor/linhagem; apresentação diferente
mantém identidade; mesma prova com mero novo rótulo não habilita operações.
O teste da última propriedade rejeita promover estado sem as testemunhas
exigidas; não prova autenticidade da declaração sintética. Dados usados no gráfico
não são selecionados por desempenho e não ganham suficiência estatística.

## Ilustração real limitada à E5b-6

O aceite registra 2025 REG **272** jogos observados, POST **13**, 2026 REG **32**
(W1–2) contra inventário de 272 IDs. Isto ilustra integridade/reconciliação aceita
e o subset arquivado 2026, não completude de jogo/modelo/tempo. O schema não emite
uma taxa da população esperada sem prova; 32/272 é só descrição do inventário
arquivado. Não rotular as médias observadas de 2025 como temporada completa.
Completude, EPA/modelo, ingestão/disponibilidade histórica e encerramento seguem
UNKNOWN. E5b-6 não entrega prova para T nem P-E. Os três PIT sem agregados ficam
intactos. Real illustration em examples.json só repete essas contagens e limites,
com referência ao aceite; não cria observationId/receipt ou proveniência nova.
