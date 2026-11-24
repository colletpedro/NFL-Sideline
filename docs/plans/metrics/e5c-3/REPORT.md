# E5c-3 — relatório candidato ao aceite

Entrega implementada e verificada localmente. Não conectada a Production,
API editorial, processo semanal ou seleção PIT. Sem merge em main, push ou deploy.

## Base, isolamento e commits

Base exata: `152313edf7d74c2175f5b3727c521e69bb71b30d`.
Branch: `codex/metrics-lab-adapter-e5c3`.
Worktree: `/Users/pedrocollet/.codex/worktrees/metrics-lab-adapter-e5c3/NFL Sideline`.
Estado inicial limpo e HEAD da base conferidos. Checkout original preservado:
HEAD/status idênticos e SHA-256 dos 40 arquivos não rastreados idênticos ao inventário.

Commits focados de implementação:

- `f2a51f5b22ece68fdf554ec1c03c4a9dfc201c0a` — desenho antes do código.
- `38d5524aa78cfa060260210640987196a82d709e` — reader → DTO, validação, processo e transporte congelado.
- `8fe586028dedf4c29ffe9a1023b5cc1577433935` — seleção e apresentação mínima, testes da UI.
- Commit documental seguinte reúne este relatório, operação e evidências; obter
  HEAD final com `git rev-parse HEAD` e `git status --short`.

## Implementação e fronteiras

Novo módulo `etl-pipeline/src/nfl_sideline_etl/metrics_lab/` chama exclusivamente
`metrics_observations.publication.read`. A leitura aceita revalida originais e
rederiva antes de qualquer redução. Nenhum componente E5c-2 foi alterado.
Configuração nominal explicita paths, classificação e pin bundleId. Não aceita
extrato de observações, snapshot de transporte salvo, relatório ou revisão latest.

`web-ui/build/observations-process.mjs` executa Python configurado pelo operador,
sem shell/.env, uma vez ao iniciar. `observations.ts` congela strings JSON e serve
rotas GET separadas pelo Vite existente, somente loopback, Host/Origin/marcador
restritos. Não há subprocesso por clique. Falhas sanitizadas não fazem fallback.
Configuração e bundles sob o allowlist estático web-ui são recusados.

O DTO transporta IDs originais, recorte, valores e denominadores exatos, garantias,
limitações e fieldScopes. Não transporta fontes, Parquets, linhagem integral,
receipts, paths ou contexto editorial. DTO/validação estrutural no browser não
provam a origem. Consulte [contrato detalhado](TRANSPORT.md) e [operação](README.md).

A interface tem modo próprio, cinco seletores e uma observação por vez. Período,
denominadores, modelo EPA não identificado e conhecimento no corte não demonstrado
ficam visíveis. Zero conhecido, denominador zero, fonte ausente, UNKNOWN e COMPLETE
vazio têm textos distintos. Defesa conserva sinal e números; frequência usa o
general da mesma população. Flags desconhecidas mantêm o aviso de contexto do
jogo inteiro, sem nova contagem por fundamento/time. BigInt/HALF_UP preserva faixa
e sinal de valores não zero próximos de zero. Não existem eixos comparativos,
ranking, diferença, superioridade, tese ou vencedor.

Cancelamento e identidades evitam mistura por respostas atrasadas. Recarga preserva
a escolha por observationId; recorte removido é informado sem troca de bundle.
Seleção em catálogo esparso continua alcançável quando um time/papel só tem outro
fundamento disponível. Browser não decide caminhos nem executáveis.

## Prova sintética e ausência de prova real

**Todos os dados apresentados nesta prova são sintéticos.** São cinco bundles
completos, 24 documentos cada: estados gerais, zero conhecido, volume sem EPA,
referência histórica POST2025 e fontes ausentes. Totais: 120 documentos; os
períodos individuais/acumulado se sobrepõem e não são amostras independentes.
Os vetores versionados reduzidos (15 DTOs) são conferidos contra a projeção
operacional; originais fechados são reconstruídos nos testes temporários pelo
construtor sintético aceito, sem E5c-1 fixture checker operacional.

Os bundles reais E5c-2/materializações E5b-6 não estavam nos paths temporários
registrados. Por orientação explícita do usuário/orquestrador, a prova real fica
**pendente**. O orquestrador informou que os quatro Parquets originais permanecem
intactos; reconstrução será separada. Não se usou `real-observations.json` como
bundle nem se fabricaram receipts reais. A entrada real configurada retornou
`BUNDLE_VALIDATION_FAILED`, sem números e sem substituição por fixture.
BAL/DAL REG2026 W1–2, NE POST2025 e lacuna BAL W3 ainda precisam dessa prova.

A sessão sintética inicial/restaurada tem ID:
`sha256:a9c839a6e35f753ef446a66ec82a3f4d1c5a29747dc91801b2276f7a13b474c9`.
Bundle sintético de estados:
`sha256:7d6e3c71116935e42fe01e3cad1c2161dff89b4776f679d1ec2d629d96b9778c`.
Os demais pins e estados constam de [HTTP](evidence/http.json).
O [DTO selecionado](evidence/transport-example.synthetic.json) preserva
observationId/dtoId e soma EPA `-0.0000000000000000000000000000001`, denominador 2,
volume 3; apresentação `−<0,001`, sem substituir por zero. Esse JSON é transporte
sintético, **não um bundle aceito nem prova autônoma da linhagem**.

## Verificações executadas e limites

| Verificação | Resultado e alcance |
|---|---|
| Python novo + E5c-2 + materialização | 109 testes passaram na rodada conjunta (7 novos + 42 E5c-2 + 60 materialização); depois 8 novos passaram, incluindo a paridade adicional dos vetores. 110 casos distintos executados |
| Frontend final | 133 testes passaram em 10 arquivos; inclui 8 novos e os cinco `it.fails` legados preservados, sem anunciá-los corrigidos |
| Lint / build | lint sem avisos; TypeScript e build público passaram |
| HTTP real | loopback 127.0.0.1:18083: 120 documentos, 12 recusas verificadas; [resultado](evidence/http.json) |
| Sessão congelada | bytes de catálogo/documento idênticos após adulteração sintética no disco; reinício recusa entrada e devolve 409 à sessão antiga; bytes sintéticos restaurados; [resultado](evidence/freeze.txt) |
| Browser real | Chrome 155.0.8059.82, desktop 1440×1000 e mobile 390×844; seleção, reload, resposta atrasada, teclado/foco, details e ausência de overflow; [resultado](evidence/browser.json) |
| Escolha removida | após reinício inválido, Chrome com preferência anterior recebeu aviso de recorte removido e nenhum article/fallback |
| Production | build sob VITE_EDITORIAL_UI/VITE_OBSERVATION_CONFIG/VITE_API_BASE_URL hostis byte a byte idêntico ao build normal; sem rotas/imports locais; [hashes](evidence/production.json) |
| Preservação | gates de escopo e 40 hashes históricos passaram; git diff --check passou |

Contraprovas incluem dependência ausente, versão desconhecida, extrato isolado,
fixture rotulada real, pin errado, observação adulterada com observationId,
bundleId e hashes externos recalculados, remoção de fieldScopes/limites,
IDs/sessão divergentes, path/query/encoding/Host/Origin/método/corpo proibidos.
As regressões E5c-2 verificam adicionalmente originais/estatísticas/associações/
proveniência adulterados e rehasheados. Nenhum hash externo transforma divergência
dos originais aceitos em RECONCILED. Os testes do cliente verificam estrutura e
identidades, sem reivindicar autenticação ou substituir essas regressões.

A prova HTTP foi realmente executada, não simulada. Não houve prova HTTP da API
Java antiga (serviço não iniciado); seus guards/proxy e testes foram preservados.
Não foram executados gates Java/SQL/ETL completo, pois não foram alterados.
Nenhuma instalação, aquisição, .env, banco remoto ou modelo foi utilizado.
Não se executou o main histórico E5c-1 com base incompatível.

## Evidências visuais inspecionadas

- [Desktop — modelo/completude UNKNOWN e EPA próximo de zero](evidence/desktop-unknown.png).
- [Mobile — COMPLETE vazio versus denominador zero](evidence/mobile-complete-empty.png).
- [Mobile — defesa e referência histórica, foco/details](evidence/mobile-history.png).

As capturas foram abertas e inspecionadas. Teclado operou summary nativo com
Enter/Space, foco visível e detalhes expansíveis; seletores são controles nativos
rotulados. Não houve participantes/protocolo: compreensão humana **não avaliada**.
Não se reivindica auditoria completa de acessibilidade ou usabilidade.
[SHA-256 das evidências](evidence/SHA256SUMS.json).

## Garantias preservadas e pendências do aceite

Os números reconciliados continuam exibíveis com completude, modelo EPA ou
conhecimento temporal UNKNOWN, com escopo/denominador/limite próximo. UNKNOWN não
vira zero ou COMPLETE, nem percentual de cobertura inventado. COMPLETE sintético
só aparece nos casos sustentados pelos vetores aceitos. Os estados reais não
foram promovidos por esta entrega e continuam UNKNOWN onde faltam provas.

O transporte só admite conhecimento temporal UNKNOWN. Compatibilidade básica
CONFLICT é recusada; semanas iguais não autorizam comparar cortes diferentes;
alvo incluído não ganha elegibilidade pregame. Comparação qualificada e conclusões
editoriais continuam indisponíveis. Elegibilidade futura de dados também não
validaria uma tese editorial.

Production, Home/detalhe público, snapshot schemaVersion 1, claims visual v1,
contratos E5a/E5c-1/E5c-2, seleção temporal, adapter, writer, SQL, Java, aprovações e
workflow foram preservados. A única ligação ao laboratório existente é pela entrada
Vite editorial e pelo modo local; não se pode ativá-la por VITE_* no build público.

Para o orquestrador: revisar fronteira/DTO/erros e aceitar a integração sintética;
reconstruir separadamente os bundles reais a partir dos originais preservados,
validar/pinar e repetir os probes HTTP/Chrome sem alterar o consumidor. Esse é o
próximo passo mínimo para colocar BAL/DAL/NE reais no laboratório. Depois, avaliar
compreensão dos números e limites com participantes e protocolo. Qualquer evolução
comparativa/editorial exige política e validação próprias, fora deste adaptador.
