# Diagnóstico inicial — inspeção interna

Protocolo congelado em `35cd8dc`, sem ajustes de UI. Navegador real IAB, 1440×1000, depois 390/320; 20 fixtures E1 percorridas por seletor, snapshots DOM arquivados localmente. BAL–DAL, CHI–BAL e NE–JAX gerados explicitamente e leitura textual expandida. Não houve participantes ou cronometragem de compreensão.

| Achado | Evidência inicial | Ajuste justificado |
| --- | --- | --- |
| Leitura rápida omite adversário/papel/período | BAL · Passe; ano/semana do jogo no cabeçalho não é período observado | Rotular ataque × defesa; incluir período de cada série e acesso ao encontro |
| Limitação distante dos sinais | Restrição após duas séries; primeiro cartão BAL–DAL 646,8 px | Mover restrição junto ao achado, antes dos pontos |
| Metadados repetidos e fonte pequena | Papéis 10 px; temporada/semanas + contagem + ano em cada ponto | Aumentar rótulos; retirar contagem redundante de semanas e ano de cada ponto, conservando período junto à série |
| Histórico pouco acessível | Topo do painel em y=2679,4 no desktop BAL–DAL | Link de acesso antes da leitura; foco no destino |
| Tabela larga sem foco próprio | 540 px, região visível 279/209 px, tabindex ausente | Região nomeada/focável e instrução de rolagem |
| Destaque verde pode parecer placar | NE–JAX quatro destaques; ambos os ataques em both-sides | Aviso próximo à leitura rápida: cor/quantidade não determinam vencedor; preservar texto de metodologia E1 |
| Panorama destacado está recolhido | CHI–BAL destaca GENERAL | Botão na leitura rápida abre panorama e move foco ao cartão |
| Repetição editorial | Limite curto repetido em highlights, quatro cartões e global; corte temporal dito duas vezes no rodapé | Não reescrever copy E1; remover só redundância estrutural de metadados e explicar lacuna editorial separadamente |

Respostas equivalentes estão presentes nos textos: BAL ataque × DAL defesa, passe/corrida, 2026 semanas 1/2, amostra curta, nenhuma previsão. Visual permite ver cada semana, texto agrega médias. Não compararemos médias textuais e pontos como se fossem a mesma estatística. CHI–BAL exige períodos separados (CHI 4/6/7, BAL 4/5/6); ambas as representações informam cobertura desigual. NE–JAX mostra variação e quatro destaques equivalentes. Não são evidências de velocidade ou acerto humano.

Geometria inicial conserva oposição, zero, pequenos sinais, extremos, unilateralidade e empate. Nenhum ajuste estatístico é necessário. Mobile não transborda horizontalmente; há tabela com rolagem interna. Contraste será medido em cores computadas e ampliação de texto será concluída após ajustar tamanhos relativos. Cinco regressões públicas continuam abertas.
