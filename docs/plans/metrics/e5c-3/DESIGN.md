# E5c-3 — desenho anterior ao código e transporte v1

Base exata 152313edf7d74c2175f5b3727c521e69bb71b30d; worktree inicial limpa,
branch codex/metrics-lab-adapter-e5c3. Checkout original inventariado: HEAD,
status e hashes de 40 arquivos não rastreados (inclui reports/research_notes).
Não alterar contratos, E5c-2, API principal ou Production.

## Fronteiras e inicialização

Usar a entrada editorial Vite existente, loopback 127.0.0.1:18083. O operador
informa NFL_OBSERVATION_PYTHON (executável absoluto) e NFL_OBSERVATION_CONFIG
(JSON local absoluto). Nenhum VITE_*, .env, descoberta ou escolha latest.
Configuração metrics-lab-config-v1: {configVersion, bundles:[{entryId,label,
dataKind:REAL_ARCHIVE|SYNTHETIC,path,expectedBundleId}]}. entryId é slug seguro;
expectedBundleId é pin obrigatório da identidade aceita. Labels não contêm paths.
Classificação REAL_ARCHIVE é declaração do operador sobre arquivo aceito, não
autenticação externa; rejeitar fixtures reconhecíveis declaradas como reais.

Plugin exclusivo editorial chama Python uma vez ao iniciar, usando execFile,
argv estruturado sem shell, ambiente mínimo com PYTHONPATH do checkout. Cada
entrada passa pela leitura pública metrics_observations.publication.read; não
ler extratos ou atalhar a rederivação. Pin comparado após validação. Falha de uma
entrada fica ERROR explícito; outras não a substituem. Configuração/subprocesso
inválidos tornam catálogo indisponível, preservando o laboratório anterior.
Stderr/tracebacks/paths não vão para respostas ou mensagens de erro do browser.

A resposta Python é adaptada por allowlist e congelada em strings/mapas privados
da sessão Vite. Não existe opção de carregar um snapshot JSON previamente salvo:
hash do transporte não comprova validação da fonte. Não ler disco por clique.
Alteração no disco exige reinício/revalidação pelo operador. Recarregar no browser
só consulta a mesma sessão; após reinício, índice e documento nunca são combinados.
Ctrl-C encerra Vite e subprocesso próprio se ainda estiver na preparação.

## Contrato interno de transporte

Separado de observation-v1, bundle-v1, claims visual-v1 e snapshot público.
Catálogo metrics-lab-catalog-v1: {transportVersion,sessionId,errorCode|null,
bundles:[{entryId,label,dataKind,status,bundleId|null,errorCode|null,
observations:[{observationId,dtoId,subject,request}]}]}.

Documento metrics-lab-observation-v1 tem dtoVersion,entryId,bundleId,observationId,
dtoId,subject,request (season/phase/origin/period), observed, values, totals,
guarantees, limitations, members reduzidos, fieldScopes, presentation e scope.
IDs originais são ligações opacas; dtoId é hash do DTO reduzido, nunca hash dos
bytes da observação original. sessionId identifica o conteúdo congelado integral.
Dados do DTO e detalhes de campos estarão nos tipos e nos vetores de teste.

Contagens/denominadores tornam-se strings inteiras exatas; epaSum/numeradores
permanecem strings decimais. Nenhum float, média de médias ou sinal defensivo
invertido. members conserva somente gameId,week,round,sourceState,completeness,
statistics; observed conserva semanas/IDs dos jogos observados. Garantias
conservam estados/motivos, coverage.expectedCount/ratio e compatibility.epaModel,
sem documentos ou IDs de receipts. fieldScopes obrigatório acompanha cada DTO.
UNKNOWN_FILTER_FLAGS_GAME_SCOPE não pode sumir. Faltas de modelo/cobertura/tempo
continuam explícitas. scope distingue SINGLE_GAME/MULTI_GAME/NO_OBSERVATION e
OBSERVED_SAMPLE/DECLARED_POPULATION, sem alegar suficiência estatística.

Nunca enviar bytes/fontes/Parquets, input/lineage, manifestos originais,
configurações/paths/locators, receipts completos ou prompts. Identificadores
fora do perfil seguro são recusados, sem truncar sua semântica. O índice usa
somente os metadados necessários à seleção. O servidor verifica a cadeia; o
cliente verifica versão/estrutura, IDs esperados, frações/contagens, flags e
limitações obrigatórias. Validação estrutural/DTO hash não autentica origem.

## HTTP da mesma entrada local

GET /__observations/ → catálogo. GET /__observations/{entryId}/{64hex} →
envelope {transportVersion:metrics-lab-response-v1,sessionId,document:DTO}.
Exigir Host exato, Origin ausente ou igual à UI, X-Local-Observations:1,
sem corpo/query/encoding/traversal; somente GET. Documento exige também
X-Observation-Session com sessionId do índice. Divergência retorna 409,
sem fallback. Entrada inválida retorna erro sanitizado. Nunca receber paths,
executáveis ou URLs pelo browser. Guard/proxy /__editorial/ permanecem.
Resposta JSON, no-store/nosniff; nenhum diretório servido estaticamente.

## Interface e isolamento

Modo novo Observações auditáveis, distinto de claims e fixtures. Seletores
bundle/time/papel/fundamento/período; uma observação por vez, sem eixos comuns,
ranking ou superioridade. Período e denominadores junto aos números, limites
visíveis, detalhes nativos expansíveis e foco nativo. CURRENT não significa
atualização: mostrar arquivo/W1–2 e ausência de garantia no corte.
Aritmética de apresentação com BigInt sobre frações, HALF_UP, faixas para não
zero arredondado a zero. Helpers SVG/Number atuais não servem para essas razões;
reaproveitar apenas a semântica decimal, não coordenadas ou gráficos comparativos.
Respostas antigas são descartadas por identidade e cancelamento; preferência
salva só por entryId/observationId. Recorte removido é informado, não substituído.

Configuração/plugin/cliente novos só entram em vite.editorial.config e
local-editorial. Build público continua pela entrada pública, sem Python/bundles,
rotas locais ou ativação VITE_*. Preservar cinco expected-failure legados.
