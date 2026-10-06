# Defeitos existentes — reprodução E0/E1

Status: **abertos**. A preparação adiciona testes, não muda o comportamento das páginas públicas. Corrigir antes da próxima publicação que use o painel antigo, ou substituir por um componente que passe os testes equivalentes.

Fonte executável: `web-ui/src/components/visual-preparation-regressions.test.tsx`.

| ID | Entrada | Comportamento exigido | Comportamento observado |
| --- | --- | --- | --- |
| TIME-01 | Pregame semana 3; só há métrica da 4 | Ausente; nunca fallback futuro | Retorna semana 4 |
| TIME-02 | Pregame semana 3; só há métrica da 3 | Ausente; dados do próprio jogo não explicam pregame | Retorna semana 3 |
| TIME-03 | Métricas em ordem 2, 1; alvo 3 | Última semana anterior = 2 | Retorna 1, depende da ordem |
| TIME-04 | Ambas as métricas da semana 2; jogo na 3 | Rótulo informa semana observada 2 | Cabeçalho declara Week 03 |
| SIGN-01 | EPA ataque −0,4 ou +0,4, adversário +0,1 | Trocar sinal muda posição/lado em relação a zero | Geometria idêntica; só texto/opacidade muda |

Os quatro testes de tempo e o de geometria usam `it.fails` do Vitest. Eles executam, confirmam que a expectativa desejada falha e exigem migração quando o comportamento for corrigido. Existe um teste positivo para confirmar extração da função e renderização real antes dos expected failures; erro na extração da função ocorre fora deles e falha o arquivo inteiro.

A função privada real é carregada por import `?raw`, extraída e transpilada em isolamento; não foi copiada/reimplementada nem exportada em Production para acomodar testes. Migrar as asserções para a API pública do substituto quando houver refactor. A geometria usa as saídas reais do componente e compara posições/dimensões, ignorando apenas cores/opacidade. Uma substituição por SVG exige adaptar essa captura mantendo a propriedade (mudança de sinal muda geometria), não simplesmente apagar a regressão.

Os testes de corte têm escopo **pregame**. Postgame precisa de contrato próprio; não proibir métricas do jogo em uma tela futura explicitamente postgame. Este gate não resolve disponibilidade histórica `asOfDate`, cobertura da fonte ou qualidade dos dados.

Responsáveis futuros: correção temporal acordada por integração/domínio; geometria e rótulos por frontend. Uma correção isolada pode anteceder E3 sem aguardar a guinada inteira.
