# E5c-3 — aceite da integração sintética, 18/10/2026

Aceita no escopo de adaptador, transporte e apresentação mínima **com bundles
sintéticos**. O gate de dados reais permanece pendente. Candidata
`b39120b15254b6fa56da17483cbce603a1633637`, base
`152313edf7d74c2175f5b3727c521e69bb71b30d`, incorporada sem correção de código
à branch local `codex/metrics-integration-e5c3`. A worktree candidata foi preservada.

## Revisão independente

Revisados adaptador Python, entrada/configuração, subprocesso, guards HTTP,
congelamento, validação do DTO, cliente, escolha de recortes, aritmética BigInt,
apresentação, fixtures, testes e scripts operacionais. A fronteira operacional
continua sendo o reader público E5c-2, que reconstrói a cadeia antes de reduzir
os dados. A validação no browser é estrutural; não autentica fontes.

Reproduzidos **110 testes Python** em uma rodada conjunta (oito do adaptador,
42 E5c-2 e 60 materialização), **133 testes frontend**, lint e build. Os cinco
expected-failure legados continuam preservados. O gate de preservação candidato
e `git diff --check` passaram antes do registro documental de aceite.

O Vite precisou de permissão de escrita na worktree para seus arquivos temporários
e saídas; as conexões loopback também exigiram permissão do sandbox. As repetições
com essas permissões passaram. Nenhuma recusa de revisão automática ficou pendente.
Nenhuma instalação, download ou leitura de .env foi necessária.

## HTTP real, usando somente dados sintéticos

Preparação própria em `/private/tmp/nfl-e5c3-orchestrator-demo-20261018`, com cinco
bundles sintéticos completos. A entrada real ausente permaneceu ERROR, sem fallback.
Servidor próprio iniciado em 127.0.0.1:18083, sem API Java.

- **120 documentos e 12 recusas HTTP** reproduzidos. [Resultado](http.json).
- Após adulteração do bundle sintético no disco, catálogo e documento congelados
  conservaram exatamente os mesmos bytes na sessão inicial.
- Reinício revalidou e recusou a entrada; a sessão antiga recebeu **409**.
  Os bytes sintéticos originais foram restaurados. [Congelamento](freeze.json).
- No checkout de integração, `prepare` reproduziu a mesma identidade de sessão
  da prova HTTP, após a restauração dos bytes.
- Servidores próprios encerrados; listener ausente e bind breve na porta 18083
  aprovado. [Encerramento](shutdown.json). Nenhum outro processo foi encerrado.

Os 120 documentos contêm períodos individuais e acumulados sobrepostos. Não são
120 amostras independentes. Uma resposta HTTP real não transforma fixtures em
dados reais de NFL. Não se exercitou HTTP do serviço Java anterior nesta revisão.

## Production e apresentação

Reproduzida a comparação byte a byte do build público normal contra build com
VITE_EDITORIAL_UI, VITE_OBSERVATION_CONFIG e VITE_API_BASE_URL hostis. Nenhuma
rota/import do laboratório entrou nos assets. [Hashes](production.json).

As capturas candidatas desktop e mobile foram abertas e inspecionadas; seus
hashes e demais evidências conferem. O orquestrador **não repetiu a sessão de
Chrome** nem as interações de teclado/respostas atrasadas em browser real;
essas provas são da candidata, preservadas e identificadas como tal. Os testes
do cliente/seleção/transporte foram reproduzidos. Não houve participantes,
avaliação de compreensão ou certificação de acessibilidade.

A interface é um leitor mínimo funcional, ainda com bastante texto de operação
e limitações antes dos números, especialmente em mobile. Uma próxima rodada de
produto deve reduzir repetição, melhorar a hierarquia e testar compreensão, sem
remover os limites necessários. Este aceite não declara concluída a guinada visual.

## Limites e próximo passo

**Prova real pendente por ausência dos bundles/materializações completos antigos.**
Não se usou o extrato real como bundle validado, não se criaram receipts reais
e não se alteraram dados para liberar o gate. Completude/modelo/conhecimento
temporal UNKNOWN continuam explícitos; não há comparação ou conclusão pregame.

Próximo passo: reconstruir e aceitar bundles reais a partir dos originais
preservados, guardando materialização e bundle completos em diretório durável,
com inventário e hashes. Novas observações/receipts/IDs, se necessários, devem
ser declarados como novos; não prometer recuperar as identidades anteriores.
Em seguida configurar pins e repetir HTTP/browser com BAL/DAL, NE POST e lacuna
de fonte. Só depois ampliar a apresentação e avaliar compreensão humana.

Reprodução dos testes e HTTP: [README candidato](../e5c-3/README.md). Os paths
temporários desta revisão são apenas de demonstração sintética reconstruível;
os relatórios selecionados estão versionados. Não são preservação dos bundles
reais perdidos. Para repetir, sempre escolher diretórios novos.

[Verificação e hashes](verification.json) registra os 38 arquivos candidatos e
40 arquivos históricos não rastreados. Código/fixtures candidatos permanecem
idênticos; contratos, E5c-2, componentes anteriores de métricas, SQL, Java,
frontend público, snapshots e workflow foram preservados. Sem aquisição, banco
remoto, modelo, processo semanal, merge em main, push, publicação ou deploy.
