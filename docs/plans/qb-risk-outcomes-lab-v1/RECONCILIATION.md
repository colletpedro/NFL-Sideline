# Reconciliação de dados, números e versões

O B2 de apresentação conserva nomes de campos próprios: `observedInterceptions`, `expectedInterceptions`, `expectedFromClassified`, `expectedFromNotClassified`, `differenceInterceptions`, `differencePer100`. O contrato M3 mantém seus campos originais; B2 não é convertido em um Index M3 com aliases ambíguos.

`package.py` verifica todos os arquivos do manifest científico e hashes das fontes, SHA exato do modelo, alvo/entrada, taxas fixas e suporte de 2025, versão/esquema do consumidor, chaves, GSIS, semana/jogo/equipes/data, situações numéricas, probabilidades e agregados. `expectedInterceptions` é a soma canônica das contribuições de ambos os grupos; cada contribuição soma as probabilidades originais. Zero passes gera indisponibilidade, nunca uma taxa inventada.

Antes da ativação inicial, 7.970 chaves/jogadores/classificação/INT/semana foram comparados com o pacote M3 original. O resultado é `sameEligiblePasses:true`, identificado por pacote M3 `d3739e3d9103c48fda1c417a`. Isso não certifica verdade do charting. Atualizações com coberturas ou revisões distintas não cortam silenciosamente a população: cada leitura usa seu pacote e identifica o recorte ativo.

O teste de artefato do frontend lê as fontes pinadas configuradas e valida cada detalhe, soma de probabilidades e os 66 jogadores × nove períodos. Renderiza o componente real de cálculo/medidas, compara as duas contribuições, quantidades, total sem arredondamento intermediário e números exibidos; também testa coordenadas em quatro larguras, total/por 100, sem filtro estatístico por volume. A suíte M3 existente confere todos os seus jogadores/períodos.

O navegador coletou 36 estados: duas leituras × duas unidades × nove períodos, com Todos os lançadores. Cada ponto DOM conserva GSIS, x/y numérico e projeção cx/cy. Foram comparados 1.372 pontos, incluindo a reta que une (0,0) e (máximo,máximo) nas projeções independentes dos eixos. Nenhuma coordenada foi afastada para melhorar legibilidade; a identificação é sob demanda. [Observações DOM](evidence/browser-chart-periods.json), [recibo](evidence/browser-reconciliation.json).

Os seis casos obrigatórios foram selecionados no navegador e comparados ao pacote. Rodgers também foi conferido nos cinco eventos de seu cruzamento não classificado/interceptado; os IDs e descrição de origem estão no recibo de evidência. [Casos](evidence/browser-real-cases.json), [evidência](evidence/browser-evidence.json).

Tolerância de reconciliação numérica entre diferentes ordens de soma/serialização: 1e-10; projeções em pixels: 1e-9. Não chamar equivalência numérica de identidade de bytes. As respostas HTTP de todos os 66 jogadores foram, adicionalmente, idênticas em bytes aos arquivos de apresentação. O replay de atualização preservou exatamente todos os 7.970 registros/probabilidades e agregados, embora o pacote de QA tenha outro ID de proveniência por manifest de fontes com escopo diferente.

As observações DOM são evidência congelada daquela execução, não uma nova visita ao navegador quando o verificador roda. Para conferir novamente seus valores contra as versões imutáveis:

```sh
python3 research/qb_risk_outcomes_lab/verify.py --out /tmp/nfl-outcomes-reconciliation-new.json
```

Publicação usa diretório temporário irmão, hashes do pacote completo, rename imutável e troca atômica de `current.json` somente B2. O servidor responde detalhes pela versão solicitada; a interface rejeita mistura de versão/identidade. Testes de resposta tardia, falha/recuperação e ativação com versão antiga preservada passaram. [Atualização de QA](evidence/update-replay.json), [publicação](../qb-risk-outcomes-lab-v1/checks/python.log).
