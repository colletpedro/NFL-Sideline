# Protocolo prévio — cobertura e clareza, revisão 1

Registrado antes de gerar qualquer caso fora dos seis conhecidos. A correção textual usa somente
esses seis e fixtures sintéticas. Seletor 2.0.0 e contrato 5 permanecem; renderer 5.0.1.

## Universo e inclusão

Inventariar arquivos JSON locais de `editorial`, `core-api/src/test/resources`, `etl-pipeline/data`
e `etl-pipeline/tests`; registrar também arquivos locais Parquet/CSV encontrados nesses diretórios.
Excluir dependências, builds, diretórios ocultos, credenciais, esta avaliação e dados públicos.
Somente objetos de contexto tático v3 com `game`, `home_team`, `away_team`, `evidence` são candidatos
a entrada direta. JSONs de resultados, textos publicados e outras estruturas não são contextos.
Não extrair evidências de prosa, não baixar dados nem transformar Parquet nesta entrega. Registrar
fontes não consumíveis e motivo; a elegibilidade final temporal/de proveniência é verificada pelo
mesmo FrozenContext do comando offline. Rejeições não serão substituídas por outros jogos.

Deduplicar primeiro conteúdo normalizado (game/teams/evidence tipadas, observações únicas ordenadas,
números decimais canônicos; ignorar mercado, janelas derivadas e metadados extras); depois game_id.
Documentar todas as origens e hashes brutos, inclusive versões divergentes do mesmo jogo. Para os
seis conhecidos usar a entrada do manifesto original; para os demais, preferir `contexts/`, depois
menor caminho lexical. Nunca combinar fontes nem completar semanas. Identidade de jogo distinta
não basta se as evidências normalizadas forem cópias. Nenhum arquivo rejeitado será contado como
um jogo adicional. Sintéticos são deliberados e contabilizados à parte.

## Histórico, seleção e estratos

Consultar metadados de cases/run/result/attempt/ledger, registros de cache em database-originals,
e registros v1/v2. Não consultar textos/resultados dos novos casos para ajustar o renderer.
Registrar IDs e presença de uso anterior, sem copiar respostas ou prompts do Gemini.
Os seis jogos do manifesto original são regressão conhecida. Outros com prova de geração/avaliação
anterior são também regressão, identificada como externa aos seis. Sem cadeia que confirme ausência
de uso, classificar `unknown` (histórico de uso desconhecido), nunca presumir novidade por pasta.
`unseen` exige proveniência afirmativa de reserva/sem uso anterior e ausência de evidência conflitante.
A lista de proveniências afirmativas nesta entrega é vazia: não há autorização para inventá-las.
O inventário pode portanto encontrar zero inéditos confirmados. Esta limitação não bloqueia o lote.

Selecionar todo universo elegível único local, sem amostragem ou escolha por saída. Não há semente
aleatória, pois é um censo determinístico. Manter quatro coortes: unseen, regression, synthetic, unknown.
Os quatro sintéticos v2 já existentes são regressões sintéticas separadas. Não inflar a amostra real.
Descritores de entrada: temporada/semana (início <=4; meio 5–12; final >=13), número e listas de semanas
por equipe, métricas ausentes, pares disponíveis, presença exata de positivo/zero/negativo por métrica.
Registrar distribuição dos estratos, sem balancear artificialmente. Estratos ausentes ficam vazios.
Lacunas são semanas esperadas ausentes, não byes. Bye confirmado exige calendário local identificado
com temporada, equipe e semana; sem tal prova, causa desconhecida. Não inferir por observação ausente.

## Congelamento e execução

Antes do lote: testes conhecidos, gate Java 21, scripts testados; registrar SHA-256 dos fontes Java,
testes, harness, docs normativos, protocolo, manifesto, entradas e JAR executado. Verificar antes e
após a execução. Preservar também hashes de frontend/dados públicos, artefatos v1/v2, avaliação Gemini
e código semântico inalterado. JAR deve ser usado sem recompilar entre congelamento e lote.
Artefatos e logs usam criação exclusiva; saída nova por rodada/caso. Sem .env: subprocesso Java recebe
apenas ambiente mínimo para Java/PATH/locale. Nunca enviar segredos ao artefato. Uma falha por caso
não interrompe os demais. Preservar result/context/claims/selection/rendered e código de saída.
Falha de processo sem result.json = harness/processo; FAILED do motor = falha do motor com código
sanitizado; validação explicitamente marcada em result.json é contabilizada separadamente.
Não corrigir implementação/protocolo após exposição. Correção indispensável exige rodada/versionamento
novo e os casos já expostos passam a conhecidos. Métricas e inspeção não selecionam novos exemplos.

## Métricas obrigatórias, com denominadores

- Inventário: arquivos vistos, estruturas não contexto, entradas candidatas, duplicatas, jogos únicos,
  selecionados, rejeitados pelo comando, por coorte. Elegibilidade de formato não é validação semântica.
- Execução: sucesso/entradas executadas; falhas de validação e categorias/entradas executadas;
  resultados direcionais/claims produzidas. Não usar INCONCLUSIVE como taxa de falta de dados.
- Cobertura: pareáveis e adequados/6 encontros por caso com seleção disponível; oportunidades/mesmo
  denominador; cada limitação/encontros (não mutuamente exclusivas). Sem oportunidade: separar presença
  ou não de pares adequados e pares com ambos os lados estritamente positivos; registrar simultaneamente
  bloqueios de cobertura e sinais. Nunca atribuir cobertura como causa única sem conferir sinais.
- Byes: casos com calendário confirmatório/casos reais; lacunas sem causa conhecida/casos reais.
- Checagens por claim principal: ambos os nomes nas linhas correspondentes, médias e faixas semanais
  com formatação controlada, semanas por janela no trecho/shared scope, método de agregação explícito.
- Checagens por MATCHUP no veredito: fundamento e par ataque/defesa identificado, sinais contrários
  atribuídos ao lado correspondente quando descritos. Verificar contra dimensões validadas e agrupamentos;
  não confundir presença de uma palavra com prova completa de semântica editorial.
- Relações, limitações e omissões: condições mecânicas são verificadas pelo validador comum; harness
  confere inventário pareável representado/agrupado, ausência de autorreferência, sinais distintos não
  ocultos por generalização, vínculo interno e suporte de recortes no texto. Indicadores textuais são
  testes de realização específicos do renderer, não avaliação humana completa.

## Indicadores exploratórios

Palavras = sequências Unicode alfanuméricas (pontuação/sinais não contam); caracteres = codepoints
incluindo espaços. Por bloco e total: lista completa ordenada, n, mediana, p90 nearest-rank (ceil(.9*n)),
máximo. n=0 resulta null, nunca zero artificial. Não há nota de qualidade/confiança/legibilidade.
Repetição por análise: 6 pares de blocos; igualdade integral exata e normalizada (casefold, espaços
compactados, pontuação removida). Adicionalmente interseção de sentenças normalizadas de >=5 palavras
entre blocos; denominador pares de blocos, exemplos preservados. Repetição numérica não é erro por si.
Comprimento/repetição são indicadores exploratórios; validade mecânica não prova qualidade editorial.

## Página e conclusão

HTML estático autocontido fora de web-ui/public, conteúdo escapado, fontes do sistema, sem CDN/API.
Filtros por coorte, cobertura, padrões e falhas; quatro blocos, detalhes de evidência e decisões;
indicadores por coorte e limitações. Testar escape, filtros e detalhes, inspecionar em navegador local.
Relatar defeitos observados separados de melhorias opcionais, sem iniciar nova rodada de ajuste.
Recomendação de integração local deve considerar falhas concretas e limites da amostra, não apenas
aprovação do validador. Avaliação Gemini continua separada e imutável.

### Complemento pré-congelamento: calendário local

O inventário registrou schedules Parquet locais existentes; serão lidos pelo Polars já instalado no
venv do ETL, sem instalação/rede. O sidecar `calendar-evidence.json` complementa o descritor inicial
sem calendário do manifesto, sem alterar seleção nem alimentar o motor. Para temporadas modernas
REG, ausência de jogo só confirma bye após checar 272 jogos únicos, 32 equipes, 17 semanas distintas
por equipe e cobertura de semanas 1–18. Usar apenas game_id/season/week/home_team/away_team. Toda
lacuna examinada é anterior à partida. Calendário completo com jogo previsto e sem métrica continua
lacuna sem causa conhecida, não bye. Congelar script, sidecar e Parquet de origem. Nenhuma saída fora
dos seis conhecidos foi consultada antes deste complemento; a regra é de auditoria de cobertura.
