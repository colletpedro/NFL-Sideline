# Acabamento de leitura v1 · relatório

Refinamento local de apresentação e navegação sobre o acervo 2026 REG W1–2. O motivador é **feedback direto do usuário**. Não foi realizada nova sessão humana, nem foram criados participantes, falas, tempos ou percentuais de sucesso. P01 e os limites da avaliação anterior permanecem conforme os documentos históricos.

## Feedback → alteração

| Feedback | Acabamento implementado | Evidência |
| --- | --- | --- |
| “Ver time” colado à sigla | Um link com logo, sigla sublinhada e nome completo; placar fora; uma parada de teclado | NE/SEA no cabeçalho, três densidades no hub e jogos do time; builders preservam contexto |
| Legenda exige combinar regras | Quatro exemplos completos usando `AttemptSymbol`, o mesmo componente das unidades | Passe/corrida × convertida/não convertida; legenda também no time |
| Exemplos e marcas têm cores diferentes; cor da equipe interfere | Grafite semântico único; círculo/quadrado, preenchimento/check e contorno/traço | Estilos computados idênticos entre exemplos e unidades dos dois ataques; nenhuma cor inline de equipe nas tentativas novas |
| Pontos sem identificação | Linha por time, logo/sigla, eixo comum 0–100%, percentual e razão sempre visíveis | 32 linhas de terceira e 31 de red zone na W1; ATL fora da escala, 0/0 sem taxa |
| Resultados pouco destacados | Percentual principal e razão próxima; tinta forte, seção com plano discreto e divisória | NE 31,3% e 5 de 16; SEA 18,2% e 2 de 11; valores da fonte |
| Destaque mobile parece cartão alto | Logos em primeiro plano, placar central entre os participantes, nomes abaixo e ação principal própria | Composição diferente dos apoios/compactos; critério de escolha por data/ID preservado |

Sacks continuam em passe, scrambles em corrida. Check significa terceira convertida. `kind` e `converted` vêm da unidade original; não houve uso de `complete_pass` ou reconstrução de marginais.

## Implementação e preservação

A nova entrada fornece um contexto React opt-in, desativado por padrão nos consumidores anteriores. Quatro arquivos compartilhados consultam esse contexto; marcação e estilos anteriores continuam no caminho padrão. A entrada própria aplica o acabamento apenas ao hub, confrontos W12 e times. Explorador, calendário anterior e piloto mantêm suas apresentações. Não duplicamos a aplicação.

`TeamIdentityLink` mantém uma âncora para logo/sigla/nome, nome acessível completo, sem placar, adversário ou links aninhados. Diretório e busca mantêm “Ver time” onde identifica o destino. “Ver confronto” segue ação da partida.

`AttemptSymbol` desenha a forma e sinal finais na legenda e nas marcas. O preenchimento e o traço são fixos em grafite; foco e seleção têm indicação azul própria sem mudar o resultado. As cores das equipes continuam nas identidades e no EPA.

`LeagueRows` verifica a permissão original e usa os pontos originais. A ordenação compara as razões por multiplicação cruzada com BigInt antes do arredondamento; empate usa sigla, sem posições numeradas. A coordenada continua derivada da razão, com a função existente de geometria. Cada linha é uma categoria de time: altura não representa uma variável numérica. Logos originais sobre papel claro não recebem filtro branco. As linhas dos participantes têm fundo, borda, marca de contorno reforçado e indicação textual acessível. Sem taxa continua fora da escala. Taxa conjunta e inclusão dos participantes permanecem explícitas.

Sem referência agregada da liga no time, novos fatos, filtros, controles de aplicação ou laboratório EPA. Explicação, escala, valores assinados, denominadores e cálculo do EPA permanecem. Modelo UNKNOWN e demais limitações não foram promovidos a garantias.

## Inspeção e refinamentos posteriores

1. Antes: referência 18105 capturada em NE × SEA/1440 e hub/390. Os problemas motivadores estão descritos no plano anterior à implementação.
2. Primeira composição desktop: legenda final e dados tinham correspondência; a escala da liga precisava alinhar suas margens com as extremidades das linhas. Alinhamento ajustado.
3. A 320 px/200%, a ação do cartão excedia a largura disponível. Passou a quebrar linha, com a legenda do resultado sem limite artificial de metade da largura. O título da semana também pode quebrar como grupo.
4. A 320 px/200%, identidades do cabeçalho disputavam largura com o placar. O cabeçalho passa a empilhar identidade/placar nessa largura efetiva, conservando fonte e nomes. Zero cortes internos nas identidades após a alteração.
5. A referência com texto ampliado usa identificação/valor na primeira linha e a escala abaixo, com domínio integral. Nenhuma fonte foi reduzida para caber. Não há rolagem horizontal ou caixa de rolagem interna na referência.
6. A conferência final a 320 px identificou logos do destaque 6 px mais largas que suas colunas. O limite máximo passou a acompanhar a largura da identidade, conservando o ativo e seu enquadramento; fontes inalteradas.
7. Destaque mobile foi conferido junto aos apoios: três colunas com logos e placar central, nomes completos e CTA única. Em texto ampliado o placar passa para uma linha central abaixo das duas identidades, preservando associação esquerda/direita. Os apoios continuam compactos.

[Antes NE/desktop](captures/before-ne-desktop.png), [depois NE/desktop](captures/after-ne-desktop.png), [antes hub/390](captures/before-hub-mobile.png), [depois hub/390](captures/after-hub-390.png), [legenda final/desktop](captures/legend-desktop.png), [liga final/desktop](captures/league-desktop.png), [NYJ × TEN/red zone](captures/nyj-redzone-390.png), [hub/320](captures/hub-320.png), [NE/320 com legenda e marcas](captures/after-ne-320.png), [liga/390](captures/league-390.png), [liga/320/200%](captures/league-320-200.png), [time NYJ/390](captures/team-nyj-390.png), [ATL/320](captures/team-atl-320.png).

Na captura de NYJ × TEN, o rótulo da razão de TEN foi ajustado ao singular: “1 de 1 campanha”. Trata-se apenas de concordância textual, sem alterar valor, unidade ou definição.

## Verificações realmente executadas

- **320 testes frontend, sem skips**, incluindo oito novos testes. Preservados os cinco `it.fails` legados. Os novos testes conferem os quatro símbolos completos, identidade e contexto, ordenação exata/empates, todas as unidades dos 32 jogos e 32 times antes/depois, 192 EPA contra o oráculo independente já existente, todos os pontos/razões e permissões, estados sem percentual, duas semanas e três densidades.
- **5 testes Python pertinentes**, 7 casos fora da seleção: reader real integral e estados de agregação/zero/ausência. Nenhum processamento Python foi alterado; não foi repetida geração ou reconciliação histórica.
- **158 requisições HTTP**: todos os documentos de time/confronto idênticos byte a byte ao pacote durável e a 18105; hashes, no-store, recusas de Host, Origin, método, marcador, pin, query, subpath, corpo e cabeçalhos duplicados. O reader de confrontos recusa identificador incompatível com 403; o de times responde 404 a time desconhecido, conforme suas fronteiras existentes.
- Lint sem avisos, TypeScript journey/configuração própria e oito builds: reading-polish, hub-team, journey, matchup, W12, real, experience e público. Público repetido com variáveis VITE adversas, sem mudar o cliente selecionado.
- Hash público JS `73f18e255b7226e7357acc9e9f81593d1610c6183a27090481a54d8f4f959ad5`; CSS `2b4ae179cefd815c1838e0a7498188a33d39ebad9856ca5e71d84a415344d41d`, idênticos à base.
- Gate de isolamento: 86 arquivos listados no pacote imutável conferidos pelos hashes; ambos os pins preservados. Python, contratos, políticas, fontes, dados públicos, clientes e arquivos históricos fora dos quatro componentes compartilhados permanecem idênticos. Referência 18105 com HEAD/árvore intactos; oito listeners anteriores mantidos. Nova instância exclusivamente em 127.0.0.1:18106, strictPort, cinco readers parametrizados para a mesma porta, CORS fechado. `git diff --check`.

Navegador: NE × SEA em 1440/390/320, identidades/cores de equipes distintas, quatro símbolos finais e 63 linhas identificadas; NYJ × TEN com 22 tentativas, quatro campanhas e TEN 100% associado a 1 de 1; Geral/Passe/Corrida e denominadores; ATL sem oportunidades e produção adversária preservada; legenda do time NYJ; destaque, apoios e compactos; texto 200%; teclado/foco, marcas, regras/auditoria; identidade → time → outro jogo → semana, preservando W2 e consulta NYJ; recarga e histórico. Estilos temporários e viewport restaurados ao final. [Recibo do navegador](checks/browser.json).

## Limites reais

A referência completa aumenta a altura da página: os 32 times são legíveis no fluxo, sem esconder linhas. Não se mede aqui a frequência de compreensão entre pessoas. As inspeções foram por agente em navegador com viewport emulado; não são teste com toque físico nem nova avaliação humana ou leitor de tela falado. Sem reconfirmação humana do esclarecimento EPA. Não há nova alegação de qualidade, prognóstico, ranking certificado, significância ou independência da referência. Sem laboratório EPA, backend, banco, ETL, publicação, merge, push ou deploy.

Entrega local pronta para avaliação na instância própria; comando e encerramento direcionado no README.

## Commits locais

- `0b3ec79`: plano e capturas anteriores à edição.
- `68e600200e26fee2a12460f09e57535c397e235a`: implementação, entrada isolada e testes.
- Fechamento documental: commit posterior nesta branch, informado no chat final e consultável por Git.

A árvore final foi conferida após o commit documental. Servidor mantido em 18106/PID 25458; encerramento somente com `kill -TERM 25458`. A referência 18105/PID 59966 permaneceu intacta.
