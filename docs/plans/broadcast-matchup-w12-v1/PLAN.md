# Entrega 4/5 · plano antes da implementação

Base limpa conferida em `d82d4a6eafb85acb3cd9c94736a2160a4036281f`, branch anterior correta. Worktree gerenciada nova `broadcast-matchup-w12-v1`, branch `codex/broadcast-matchup-w12-v1`. Referências e servidores preservados. Sem rede, banco, credenciais ou Gemini.

1. Inventário nominal dos 32 jogos / 64 ataques em `inventory.json` e `MATRIX.md`; cruzar calendário congelado (resources FILE do input autocontido) com inventário PBP e observações originais.
2. Novo contrato privado `broadcast-matchup-w12-v1`: índice pinado e um documento/hash por jogo, duas referências semanais; copiar fisicamente fontes verificadas, rederivar tudo no reader, publicar por rename exclusivo. Guardar pacote e recuperação fora da worktree e reproduzir a partir da cópia.
3. Generalizar projeção/política sem alterar o contrato do piloto: identidades, semanas, seis EPA próprios, unidades reais, campanhas com todos os desfechos e fatos exatos das três famílias autorizadas. Estados e permissões por operação independentes.
4. Entrada experimental própria em 18104, loopback/strictPort, reader integral antes da disponibilização, inventário fechado de IDs e bytes congelados; rotas/métodos/autoridade/origem/marcadores/corpo restritos. Nenhuma dependência pública/VITE_*.
5. Reutilizar estrutura/estilo do piloto e calendário existente. URL `/?view=matchup-w12&game=ID`, season/week opcionais conferidos; preservar semana/filtros no retorno. Piloto/explorador e demais entradas continuam disponíveis.
6. Auditor independente dos brutos e sources (sem importar projetor/política), testes negativos e sintéticos separados, HTTP integral dos 32 documentos, navegador nos 32 IDs e matriz visual 1440/390/320, teclado/200%/falha/troca rápida. Lint/TypeScript/builds e isolamento. Commits locais e árvore limpa.

## Inventário e decisões

As fontes duráveis do piloto contêm cópias integrais dos bundles situacional e das 588 observações, inclusive `shared-source/input.json` com calendários embutidos. O pin do piloto autoriza somente sua leitura original; a coleção receberá identidade e política novas. As recuperações anteriores (materializado/input e Parquets) estão inventariadas na procedência original, mas não serão dependências da coleção autocontida.

Disponível: 32 jogos 2026 REG W1–2, 16 por semana, 32 times distintos em cada semana. Terceiras: 64 ataques AVAILABLE. Red zone: 62 AVAILABLE e 2 NO_OPPORTUNITIES (identificadas na matriz). EPA: 192 observações ofensivas individuais, três fundamentos por ataque, valores presentes; espelhos defensivos correspondentes representam a mesma amostra. Sem SOURCE_ABSENT/INSUFFICIENT reais nessas famílias; serão cobertos por testes separados. Não completar dados ausentes.

Unidades: EPA = elegíveis classificados e subconjunto de EPA finito, soma decimal original e precisão própria; terceira = game/play e cruzamento real distância/tipo/conversão; red zone = game/fixed_drive com evidências de entrada e terminal. Referências = uma produção ofensiva/time/semana, taxas inexistentes excluídas e inventariadas; W1 não mistura W2 e W2 não usa agregado. Sem referência EPA da liga.

Pressupostos exclusivos a remover em novos componentes/projetores: constante GAME/NYJ/TEN/W1, weeks=[1], política limitada ao período piloto, fatos nominais, apenas terminais TD/FG, destaques CSS NYJ/TEN, título/retorno fixos e texto temporal W1. Os módulos antigos permanecem íntegros.

Calendário: identidade exata gameId/2026/REG/week/away/home, trio de placar integral da mesma linha preservada ou trio ausente; nenhum score derivado de PBP. Data não comprova conhecimento histórico. Mercado do mesmo schedule, bruto/arquivado e temporal UNKNOWN.

Identidade visual aprovada preservada, sem nova exploração. Escopo 5/5 excluído: páginas de time, agregados e reorganização do hub. Nenhuma nova sessão humana; N=1 anterior não se torna validação ampla.
