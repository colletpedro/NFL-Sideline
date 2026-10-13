# E5b-6 — protocolo anterior à carga

Base exata `f8a258b64116aa7f67f4d4d6253d3f00dc91f5e2`, branch
`codex/metrics-backfill-e5b6`, worktree inicialmente limpa. Nenhum arquivo não
commitado do checkout original foi copiado como implementação.

Descoberta restrita a `etl-pipeline/data` do projeto e ao `sourceRoot` nominal
registrado em E5a/E5b-1. Inventariar todos os Parquets dessa raiz; selecionar
2025 e 2026 somente com calendário canônico e todas as partições PBP existentes.
2023 fica inventariada e excluída pelo limite de duas temporadas. Nenhuma seleção
por resultado, semana, jogo ou EPA. Limites preventivos: 8 arquivos, 256 MiB,
150.000 linhas PBP e 1.000 jogos no lote. Ultrapassar interrompe antes da carga.

Congelar cópias byte a byte em workspace novo, comparar inventário e SHA-256
antes/depois, registrar schema inteiro, contagens, fases, semanas, participantes,
sobreposições e diferenças com os hashes históricos. Ausência/corrupção são falhas
explícitas, nunca substituídas por PBP vazio. Metadata null: nenhuma prova de
COMPLETE, versão EPA, fim de evento ou disponibilidade histórica é adicionada.
A origem nflverse/nflreadpy é declarada pelas auditorias anteriores; os bytes e
hashes são a evidência local, sem autenticar a aquisição upstream.

Aceite mecânico: plan real; pipeline CLI local skip-acquire em instância própria;
calendário SQL igual ao inventário; auditor independente lê os bytes com Polars
sem usar o adapter, normaliza/deduplica a projeção contratual, valida join/fase/
round/participantes e filtros disjuntos, soma por `Fraction(Decimal(str(value)))`.
Confrontar todos os grupos/game audits/SQL e IDs de conteúdo/cobertura/conjuntos,
nunca médias semanais como prova de somas. Calendário sem observação mantém
cobertura UNKNOWN sem grupos. Legado é auditado com sua seleção/filtros próprios;
suas médias float são apenas diagnósticos com tolerância declarada, não prova da
igualdade exata das somas novas.

Reexecução: destino/tentativa/run novos, mesmas cópias/metadata/archive; zero
INSERTs privados, IDs iguais, todas as linhas SQL e persisted_at idênticos,
blobs/receipts e journals anteriores preservados. Revisão real só quando existem
bytes distintos locais; não inventar correção. Casos de referência determinados
por ordem lexical e condições observadas, não por relevância editorial.

Materializar seleção nominal de ambos os lotes completos, sem documentos
históricos artificiais. input-v3 → 1.1.0 → result-v3, PIT com corte explícito
`2026-10-13T00:00:00Z` (12/10, 21h Fortaleza), sem alegação de pregame certificado.
UNKNOWN/sem agregados é esperado. JAR reconstruído offline Java 21. Calendário
completo em quantidade não implica calendário certificado ou PBP completo.

Reutilizar harness E5b-5/E5b-2 apenas como código: root/UUID/banco/porta novos,
logins separados não administrativos, configs explícitas. Admin somente prepara
a instância própria. Encerra em finally, confirma pg_ctl=3, PID ausente, listener
próprio ausente e bind livre; preserva os dados desligados e evidências locais.
Sem aquisição, .env, rede remota, modelos, alterações aceitas, publicação/push/
merge/deploy. Supabase completo/advisors pendente.
