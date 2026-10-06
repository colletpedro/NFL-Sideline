# Preparação E0/E1 — coordenação da evolução visual

Data: 06/10/2026. Este pacote concretiza o [plano de evolução](../2026-10-06-visual-analysis.md). A sessão atual é responsável pela integração/produto; backend e frontend serão abertos depois, em worktrees separados sobre o mesmo commit.

## Cinco ações iniciais

| Ação | Entrega |
| --- | --- |
| Consolidar a base | Checkpoint da interface local `3a06bbb`; [inventário e verificações](checkpoint.json) |
| Fechar o documento visual | [Contrato interno v1](../../../contracts/visual-analysis/v1/README.md), schema e vocabulário finito |
| Definir estados | [Matriz](states.md); 20 fixtures válidas e 15 inválidas com erro esperado |
| Desenhar desktop/mobile | [Fontes do wireframe](wireframe/index.html); materialização e operação na matriz |
| Reproduzir erros e preparar frentes | [Cinco defeitos abertos](known-defects.md); [backend E2](work-orders/backend.md) e [frontend E3](work-orders/frontend.md) |

O protótipo não está ligado à API nem ao build público. As fixtures são sintéticas, não substituem a avaliação editorial independente. A próxima entrega funcional é E2/E3; E4 avaliará compreensão.

## Base versionada e arquivos históricos

O checkpoint contém 26 arquivos da interface local pendente. Foram preservados fora dele `Handoff.md` e os 35 arquivos de diagnóstico/proveniência históricos. Não usar `git add .` nesta árvore; artefatos locais históricos e de runtime continuam separados.

No checkpoint passaram novamente 118 testes Java, 48 frontend, lint/build e 79 testes do ETL. Os 15 testes Python citados na entrega anterior eram outro escopo (scripts); não comparar as contagens como se fosse a mesma suíte. Evidências HTTP/browser anteriores permanecem identificadas por sua data; não foram reexecutadas para o checkpoint.

## Decisões fechadas para começar

- Português; compreensão rápida do confronto; tema escuro/lima; detalhe opcional.
- Quatro encontros visíveis, geral preservado em detalhe; destaque com ressalva visível; empate sem desempate.
- Observações semanais com unidade, origem, amostra e escala comum; nenhuma nova média, confiança ou previsão.
- Preservar seletor/claims/renderização textual e históricos. Novo documento é projeção validada, não análise calculada pelo frontend.
- Protótipo sintético agora; produção estática e schema v1 intocados. ETL, recortes novos, BASIC/FULL e publicação ficam para outras entregas.

## Protocolo de coordenação

1. O orquestrador fornece o commit comum final deste pacote e verifica o freeze do contrato.
2. Abrir E2 e E3 em worktrees distintos a partir dele. O checkpoint sozinho não contém o contrato; não iniciar só de `3a06bbb`.
3. Backend e frontend seguem as ordens de trabalho. Schemas/fixtures/vocabulário compartilhados têm dono na integração. Uma necessidade de alteração deve vir acompanhada de exemplo mínimo e impacto, antes da edição divergente.
4. Cada frente entrega commits locais, testes e limites. A integração incorpora commits em sequência e executa os gates cruzados, incluindo HTTP real.
5. Frontend com fixtures é progresso, não integração completa. Não chamar duas implementações separadas de entrega concluída sem exercitar o caminho real.
6. Correções públicas de sinal/tempo são prioritárias antes de publicar o painel antigo e podem ser uma tarefa separada. Expected failures não dão autorização para publicar com erro conhecido.

Nenhuma sessão adicional foi criada nesta preparação. Os documentos E2/E3 podem ser usados diretamente como instruções quando forem abertas; não é necessário reconstruir o contexto inteiro por mensagens.

## Verificar/reproduzir

```bash
python3 scripts/verify_visual_contract.py
python3 -m unittest discover -s scripts -p 'test_visual_contract.py' -v
npm --prefix web-ui test
npm --prefix web-ui run lint
npm --prefix web-ui run build
```

Para a base Java, usar Java 21 e `mvn -f core-api/pom.xml -o clean verify`; para ETL, `etl-pipeline/.venv/bin/python -m pytest etl-pipeline`. Instalação inicial de dependências não faz parte do modo offline de geração.

Relatório final da preparação: [verification.json](verification.json). O `freeze.json` do contrato registra hashes do schema/vocabulário/fixtures; não implica qualidade editorial comprovada e não impede evolução coordenada por versão.
