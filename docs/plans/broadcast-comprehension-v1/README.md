# Compreensão da página de confronto · entrega 3/5

**Preparação concluída; coleta humana pendente.** Entrega 3/5 ainda não concluída. Recomendação atual: **evidência ainda insuficiente para decidir** sobre avançar para 4/5.

## Kit para conduzir

1. Abrir [o piloto preservado](http://127.0.0.1:18102/?view=matchup-reading), na versão exata da entrega 2/5.
2. Compartilhar somente [PARTICIPANT.md](PARTICIPANT.md) com a pessoa, apresentando uma tarefa por vez. Não compartilhar a chave de conferência.
3. Quem conduzir lê [MODERATOR.md](MODERATOR.md) e [PROTOCOL.md](PROTOCOL.md) antes da primeira sessão.
4. Copiar [RECORD-TEMPLATE.md](RECORD-TEMPLATE.md) uma vez por participante (P01…P05). Devolver as fichas anonimizadas nesta conversa. Campos não observados ficam explícitos, sem reconstruir falas/tempos de memória como se fossem registros exatos.

São 4–5 pessoas adultas que acompanham NFL, participação voluntária, cerca de 10–15 minutos cada, sem nomes/contatos ou gravação. Não explicar EPA, gráficos ou navegação antes da tentativa; ler os enunciados fixos e registrar o espontâneo antes dos complementos. “Não sei” é uma resposta válida. Não foram contatadas pessoas nem enviadas mensagens.

O link é loopback: funciona no computador que hospeda o servidor, não abre esse computador digitando 127.0.0.1 em outro celular. Nenhuma porta foi exposta à rede. Celular físico só entra se houver ambiente de acesso já autorizado para a mesma versão/pacote; confirmar integridade antes da sessão. Se inviável, realizar em computador e registrar a limitação. Emulação pode conferir funcionamento, mas não conta como toque físico ou sessão em celular.

## Devolução curta nesta conversa

Se preferir notas compactas à ficha detalhada, copiar este bloco para cada pessoa. Em cada linha de tarefa, incluir **resposta; evidência/número; caminho; dúvida/erro; ajuda; conclusão** (correta/parcial/incorreta/não observado). A classificação pode ficar pendente de análise se não estiver clara; preserve a resposta. Marcar literal ou paráfrase. Dispositivo/largura valem para todas as tarefas, salvo mudança anotada.

```text
ID P__ | Data/fuso: | Adulto/acompanha NFL/concordou voluntariamente:
NFL (frequência): | EPA (familiaridade): | Estatísticas avançadas:
Já conhecia a página/participou antes?:
Dispositivo/navegador/largura: | Mouse/teclado/toque físico/emulação:
T1:
T2:
T3 espontâneo:
T3 após complemento (taxa, contagem, sentido do 100%):
T4 espontâneo (conceito, sinais, denominadores):
T4 após pedido de passe (ação e resposta):
T5:
T6:
Interrupções/ajuda/explicações finais/limitações ou pedido de omissão:
```

Não preencher uma linha vazia como erro nem reconstruir uma fala inexistente; indicar “não observado” e o motivo. Distinguir desconhecimento de EPA de dificuldade para encontrar o controle/evidência.

## Referência preservada

- Base confirmada limpa: `c5be5b0dbb525faea85fab350039d8a5c1c87af5`, branch `codex/broadcast-matchup-reading-v1`.
- Worktree isolada gerenciada: `/Users/pedrocollet/.codex/worktrees/broadcast-comprehension-v1/NFL Sideline`, branch `codex/broadcast-comprehension-v1`.
- Piloto: 18102, PID 97976, 127.0.0.1/strictPort. Nenhum servidor novo foi necessário. Não encerrar o piloto durante a coleta.
- Referências 18098, 18099, 18100 e 18101 mantidas com os listeners existentes. PIDs e verificações em [checks/technical.json](checks/technical.json).
- Pacote: `/Users/pedrocollet/Downloads/NFL Sideline/editorial/local-artifacts/broadcast-comparison-foundation-v1/20261023-v1/bundle-reconciled`.
- Pin: `sha256:b10a2028f26d6acc229f80bbd27269016dd2e6b2e4b432a6d8a9109f643e5ee4`.
- [Captura anterior à coleta e a qualquer refinamento](evidence/reference-before.jpg), [estrutura acessível](evidence/reference-before-ax.txt), [estado inicial pronto para a coleta](evidence/initial-viewport.jpg), [percurso técnico pelo agente](evidence/technical-walkthrough.json). Essas evidências não são respostas humanas.

A experiência não foi alterada. As três suspeitas (explicação EPA, identificação dos times nos pontos, extensão mobile) continuam hipóteses. Não há novo controle, texto de interface ou refinamento aplicado antes da coleta.

## Estado e continuação

[REPORT.md](REPORT.md) separa verificação técnica, coleta, interpretação, refinamentos, reconfirmação e pendências. [results/README.md](results/README.md) registra a inexistência de resultados humanos nesta preparação.

Ao receber as fichas: preservar respostas anonimizadas, distinguir observação/interpretação/hipótese, aplicar os critérios previamente fixados, associar cada ação a evidências e só então editar a interface. Se houver edição, repetir as tarefas afetadas com pessoas reais quando viável, registrar aprendizado de quem repetiu e fazer os gates técnicos proporcionais. Sem reconfirmação, não declarar problema resolvido.

Para reproduzir a verificação técnica desta preparação, na raiz da nova worktree, com os servidores ativos:

```sh
'/Users/pedrocollet/Downloads/NFL Sideline/etl-pipeline/.venv/bin/python' -B docs/plans/broadcast-comprehension-v1/verify_preparation.py
git diff --check c5be5b0dbb525faea85fab350039d8a5c1c87af5
```

Sem merge, push, deploy, publicação ou promoção automática. O HEAD da preparação é informado na entrega do chat e pode ser obtido por `git rev-parse HEAD`.
