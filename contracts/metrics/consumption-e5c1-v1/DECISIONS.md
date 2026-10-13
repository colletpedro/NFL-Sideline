# Relação com contratos e decisões recomendadas

| Contrato existente | Reuso / fronteira E5c-1 |
|---|---|
| E5a v1 CONTRACT/contract.json/PROVENANCE | Fórmulas, 22 IDs, B/E, defesa permitida, exact sums e apresentação; não alterar congelamento |
| E5b-1/2 | Origem única de statistics/coverage/manifest/linhagem offline e persistida; ausente não tem grupo. Novo documento não recalcula identities ou altera writer |
| E5b-3 correção 1.0.1 e aceite | Razões, assinatura período, tempos exclusivos, UNKNOWN e comparação conservadora de eficiência. Novo escopo ARCHIVED_DECLARED_PERIOD é inventário descritivo nominal, não modo temporal alternativo |
| E5b-4 inicial / revisão | História preservada; bloqueio calculation_id por jogo foi resolvido pela entrega de identidades, não repetir seu modelo |
| Identidades E5b-3/4 e aceite | Lote/cobertura/associação/revisão separados, input-v3/algoritmo1.1.0/result-v3/materialization-v2 intactos. Novo observationId é derivação adicional, não alias |
| E5b-6 / aceite e real-proof-summary | Integridade/reconciliação de fontes locais reais: 272 REG2025, 13 POST2025, 32 REG2026 W1–2. População completa por jogo/modelo/tempos/FINAL não demonstrados; PIT vazio não fornece números |
| Visual v1 / editorial / snapshot | Não há compatibilidade anunciada, adaptação, endpoint ou publicação. Integridade de documento não valida tese |

Referências normativas/históricas lidas: [E5a](../e5a-v1/CONTRACT.md),
[proveniência E5a](../e5a-v1/PROVENANCE.md),
[E5b-3](../../../docs/plans/metrics/e5b-3/CONTRACT.md),
[aceite corrigido](../../../docs/plans/metrics/e5b-3-review/CORRECTION-ACCEPTANCE.md),
[E5b-4](../../../docs/plans/metrics/e5b-4/CONTRACT.md),
[revisão inicial](../../../docs/plans/metrics/e5b-4-review/REVIEW.md),
[identidades](../../../docs/plans/metrics/identities-e5b34/CONTRACT.md),
[aceite](../../../docs/plans/metrics/identities-e5b34-review/ACCEPTANCE.md),
[E5b-6](../../../docs/plans/metrics/e5b-6-review/ACCEPTANCE.md).
Spec.md e docs/current-state.md permanecem fontes do estado do produto.

## Decisões candidatas fechadas

1. Observações arquivadas reconciliadas com UNKNOWN são exibíveis como bytes
   observados; separar a origem dos resultados PIT. Sem rótulo de confiança.
2. Garantias independentes com motivos/IDs. CONFLICT de declaração é estado
   necessário para não esconder divergência; não é score nem novo estado SQL.
3. Escopos INDIVIDUAL, OBSERVED_SAMPLE, REQUESTED_POPULATION e PREGAME_DATA
   pertencem à decisão de operação, não níveis globais de qualidade.
4. Volume/frequência em amostras explícitas podem ser comparados sob S-V/F;
   eficiência fica restrita a P-E, mantendo a política conservadora aceita.
5. Melhor/pior não se aplica a volume/frequência. Para eficiência, apresentação
   usa direção numérica delimitada, não superioridade de time. Pregame nunca
   habilita automaticamente tese, vencedor ou vantagem.
6. Ratios exatos e configuração de apresentação separada da identidade. Não
   inserir limiares de amostra, ajustes por adversário ou incerteza estatística.

## Alternativas ainda abertas (não permissões vigentes)

- Comparação EPA/SR estritamente amostral: poderia ser descritiva com modelo
  conhecido e seleção transparente, mas exige política própria e avaliação de
  comunicação; v1 recusa. Não promover UNKNOWN por renomeação.
- Formato físico do bundle de linhagem para transporte visual (embutido versus
  referências resolvíveis): escolher na projeção; ambos precisam conferir bytes.
- Autoridades/origens confiadas, autenticação/relógios, política de conflito e
  suporte de completude/modelo: determinar por fonte na coleta; fixtures não
  aprovam uma autoridade real. Evento final exato permanece proposta separada.
- Layout lado a lado recusado: aceitar só após inspeção de que a mensagem e a
  separação não sugerem comparação; default seguro é seleção individual.

## Implementações seguintes

**a) Projeção/consumidor visual descritivo:** recuperar escolhas nominais do
caminho aceito offline/persistido, validar bundle, emitir este documento e adaptar
UI com D e recusas locais. Testar zeros/gaps/UNKNOWN, rótulos próximos e separação
visual. Sem concluir pregame nem conectar a principal implicitamente.

**b) Coleta prospectiva:** definir autoridade e evidência por fonte, append-only
receipt/ingestão/FINAL/completude/modelo e correções/conflitos. Fazer entrega
operacional própria com migrations/coleta autorizadas; não retrodatá-las.

**c) Comparação e elegibilidade editorial:** implementar decisões por operação
com S/P e seleções PIT aceitas. Validar transporte de dependências e comunicacão.
Depois avaliar regra editorial em protocolo próprio, sem tratar elegibilidade de
dados como validação da tese. Integração, aprovação humana e publicação são etapas
separadas. Nenhum desses implementadores é entregue neste pacote.

Aceite pendente: revisão independente do formato, política S/P/T, schema/vetores,
preservação e limites; escolher alternativas abertas quando forem necessárias à
etapa seguinte. Pendências E4/BASIC/FULL/legadas/Supabase completo não encerradas.
