# Auditoria final do acervo local W1–7

**Conclusão: apto para encerrar o acabamento do site e iniciar, em outra sessão, a definição do primeiro modelo.** A auditoria encontrou uma inconsistência pequena na busca semanal e uma concordância textual; ambas foram corrigidas e conferidas novamente. Não restou falha funcional bloqueante nos cenários executados.

Ambiente: `127.0.0.1:18111`, worktree `broadcast-score-curve-v2`, branch `codex/broadcast-score-curve-v2`. Base recebida: `cd5f5aac0f739ac2a0a1e04266c026602f8f933d`. Correção de código: `7a70e60e9710c838a5a612aeb80b71e3cd6550ee`. O servidor existente PID 83042 foi mantido; nenhuma outra versão foi encerrada. Sem merge, push, deploy ou publicação.

## Bug corrigido

Com `?season=2026&week=7&q=BUF&scope=week`, o resultado dizia zero partidas na W7, mas as sugestões ofereciam BUF–HOU/W1 e outros jogos anteriores. Buffalo folga na W7. A busca agora usa a mesma população de jogos nas sugestões e nos resultados. O acesso à página do time e à busca da temporada permanece disponível.

Também saíram “1 times” e “1 partidas”: agora são “1 time” e “1 partida”. A alteração de implementação ficou restrita a `web-ui/broadcast-journey/hub-team/Hub.tsx`; nenhum cálculo, contrato ou pacote de dados mudou.

[Antes, registro](evidence/search-scope-before.json) · [Depois, 11 cenários](evidence/search-scope-after.json) · [Captura](evidence/search-scope-after.png).

## Cobertura no navegador

Os destinos foram descobertos nos links dos sete hubs, sem abrir dados externos: **7 hubs, 107 confrontos e 32 times**, total de **146 páginas distintas**.

| Execução | Aberturas | Resultado |
| --- | ---: | --- |
| Desktop, 1440 px | 146 | Sem alertas inesperados, logos quebradas, valores NaN/undefined/Infinity, âncoras sem destino, IDs duplicados, caminhos SVG inválidos ou overflow horizontal detectados |
| Mobile, 320 px | 146 | Mesmas verificações, sem ocorrências |
| 320 px, fonte raiz 32 px (200%) | 146 | Sem overflow horizontal ou falha de vínculo entre campanhas e EPA |

São **438 aberturas inspecionadas**, além das interações abaixo. A varredura inicial descobriu o problema de escopo em uma exploração direcionada da busca; depois da correção, a busca foi reconferida nas sete semanas e nos dois escopos, os hubs passaram pela checagem com fonte ampliada e os testes/builds foram repetidos. As páginas de jogo e time não receberam alterações nesta rodada.

- **Busca:** primeira letra, nomes, siglas, aliases LAR e NY Jets, ausência de resultados, teclado com setas/Enter, retorno mantendo `q=BAL`, semana e escopo. “Pats” não é um alias cadastrado e retorna ausência normalmente; não foi adicionado como nova funcionalidade.
- **EPA e navegação:** Geral/Passe/Corrida, recarga preservando o fundamento na URL e retorno hub → time → confronto. Um confronto representativo por semana recebeu as três seleções.
- **Cronologia:** cinco seleções por jogo representativo — quatro quartos e jogo inteiro. Todos os **nove confrontos com prorrogação** foram abertos e tiveram a prorrogação selecionada. Períodos sem pontuação não viraram dados inventados.
- **Classificações:** temporada → semana → temporada, expansão das duas classificações e participantes preservados. Os inventários semanais respeitam folgas; a lista completa e a posição não criam taxas para fontes insuficientes.
- **Visitas da red zone:** expansão em um jogo de cada semana, contagens e jogadas presentes sem overflow. A reconciliação independente continuou cobrindo integralmente os 107 jogos.
- **URLs incompatíveis:** 13 casos — temporada, semana, fase, time inexistente, identidade conflitante, duplicações e fundamento inválido — exibiram erro recuperável, sem métricas de outro confronto.
- **Falha de rede:** a rede foi desligada apenas na aba temporária da auditoria, durante navegação para CIN × BAL. A interface retirou os dados anteriores e mostrou erro. Após restaurar a rede e usar “Tentar carregar novamente”, recuperou CIN × BAL. As condições da aba foram restauradas e ela foi fechada.
- **Console:** nenhum erro inesperado antes da injeção de falha. A falha de rede foi intencional e está registrada separadamente.

Evidências: [rotas](evidence/routes.json), [páginas](evidence/browser-pages.json), [texto 200%](evidence/text200.json), [prova da fonte raiz](evidence/font200-proof.json), [busca](evidence/search.json), [navegação](evidence/navigation.json), [controles](evidence/controls.json), [prorrogação](evidence/overtime.json), [URLs inválidas](evidence/invalid-urls.json), [recuperação](evidence/offline-recovery.json), [console antes das contraprovas](evidence/console-before-faults.json).

## Testes, dados e isolamento

- **370 testes frontend**, 38 arquivos, passaram na versão corrigida; cinco falhas esperadas legadas preservadas.
- **714 testes Python distintos passaram.** A primeira execução sem as fontes privadas teve 693 sucessos e 21 skips. Com as fontes configuradas, foram 711 sucessos e três skips; os três casos privados de comparison-foundation foram então executados e passaram. O script reproduzível já inclui essa última variável, para permitir a execução completa sem esses skips. Não se somaram reexecuções como testes novos.
- TypeScript e lint passaram; o lint mantém um aviso de Fast Refresh herdado em `reading-polish/main.tsx`, sem erros.
- Nove builds experimentais e dois builds públicos, incluindo configuração adversa por variáveis, passaram. O JS/CSS público mantém os hashes anteriores.
- **142 respostas HTTP** continuaram idênticas aos pacotes pinados. **723 campanhas, 2.096 jogadas elegíveis e 2.521 contextos** foram confrontados com a fonte congelada, sem divergência. Somas e médias exatas preservadas.
- Fonte, contratos, snapshots públicos, backend, ETL e configuração de produção permaneceram intactos. [Isolamento](checks/isolation.json) · [reconciliação](checks/reconciliation.json).

## Reprodução

Na raiz desta worktree:

```bash
# Servidor existente; não iniciar outro se 18111 já estiver ocupada pela instância correta.
docs/plans/broadcast-score-curve-v2/run-local.sh

sh docs/plans/broadcast-final-audit-v1/checks.sh
sh docs/plans/broadcast-final-audit-v1/python-checks.sh
PYTHONPATH=etl-pipeline/src PYTHONDONTWRITEBYTECODE=1 \
  '/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' -B \
  docs/plans/broadcast-final-audit-v1/verify.py
python3 docs/plans/broadcast-final-audit-v1/check-isolation.py
```

A automação do navegador usou uma aba separada, os links renderizados, controles semânticos e inspeção de DOM; os resultados estruturados estão em `evidence/`. Não houve toque físico, novo estudo com pessoas, inspeção visual humana de cada uma das 438 aberturas ou auditoria de uma publicação remota. O escopo é a experiência experimental local em 18111; versões históricas não receberam nova avaliação completa. A aprovação visual do usuário continua sendo a referência, sem reabrir a coleta humana encerrada em N=1.

[Passagem para a sessão de modelos](HANDOFF-MODELS.md).
