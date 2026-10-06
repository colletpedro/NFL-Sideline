# Interface editorial local — 05/10/2026

Implementada a interface de desenvolvimento em `web-ui/local-editorial`, com tema escuro/lima, seleção de contextos, geração explícita, quatro blocos de leitura e histórico persistido no servidor. O cliente local e seu proxy não integram o build público.

## Escopo e versões

- UI 1.0.0 e HTTP 1.1.0: catálogo de metadados e histórico de tentativas completas com hashes verificados.
- Serviço 1.0.0, seletor 2.0.0, claims v5, renderer 5.0.2 e artefato 3 preservados.
- Nenhuma chamada ao Gemini, modelo local, banco ou fonte externa; não houve leitura de `.env`, instalação de dependências, alteração de análises aprovadas ou snapshots, commit, push ou deploy.
- Datas opcionais do catálogo vêm dos arquivos de origem e são apresentadas como corte informado. Não entram na identidade canônica nem acrescentam garantia point-in-time.

## Evidências

[Verificação estruturada](verification.json) registra o HEAD de origem, os resultados dos gates, as 21 requisições HTTP de teste e a contagem de arquivos protegidos conferidos contra o HEAD.

| Verificação | Resultado |
| --- | --- |
| Java 21 `mvn -f core-api/pom.xml -o clean verify` | 118 testes; nenhuma falha, erro ou skip |
| Paridade histórica Java | 21 casos anteriores preservados |
| Frontend | 48 testes; lint e build aprovados |
| Python dos scripts | 15 testes no virtualenv existente do ETL |
| Proxy e API em HTTP real | 21 verificações; 16 contextos no catálogo |
| Separação de Production | Build/mode production da configuração editorial recusados; bundle público sem marcadores do cliente local |
| Navegador desktop e mobile | 1440 × 1000 e 390 × 844; sem overflow horizontal |
| Recuperação | Tentativa original recuperada após reiniciar API e recarregar página |

As verificações HTTP exercitam Host, Origin, header da UI, métodos, corpos, query, percent-encoding, ausência de CORS, catálogo, consulta e duas gerações com IDs diferentes e identidade semântica igual. A API continua rejeitando Origin direto.

No navegador foram exercitados API inicialmente desligada, reconexão, catálogo vazio de tentativas, geração BAL–DAL, segunda geração, recuperação da primeira, erro de histórico com API desligada, recuperação após reinício e LV–NO com desigualdade pequena e identificação expandida. Após recarregar com a API ativa, não houve erro ou warning de console; falhas HTTP durante os testes deliberados de indisponibilidade são esperadas.

O primeiro gate Java identificou que `FrozenContext` omite datas opcionais do contexto canônico. O catálogo passou a preservar somente os metadados permitidos da origem, sem alterar essa normalização; o gate completo posterior passou. A primeira execução Python usou o interpretador do sistema sem Polars; os 15 testes passaram no virtualenv existente, sem instalar pacotes. Esses diagnósticos não são falhas pendentes.

## Reprodução e arquivos locais

[Iniciar, operar, verificar e encerrar](../../docs/local-editorial-ui.md). O catálogo de demonstração usa os 16 casos conhecidos de setembro, sem atualização de dados da temporada.

`runtime/results/`, `runtime/http-checks.json`, `runtime/desktop.png` e `runtime/mobile.png` permanecem arquivos locais ignorados, reproduzíveis pelos comandos e pelo fluxo descrito. `verification.json` preserva as requisições e seus resultados observados; não presume que as tentativas ou capturas locais estarão presentes em outro checkout.

## Limites

Não houve avaliação editorial independente. A apresentação facilita examinar resultados, mas não comprova qualidade de tese, contraponto ou fluidez. Persistem a definição BASIC/FULL, o contrato das métricas prioritárias e a integração futura ao processo editorial de publicação. O histórico não tem paginação e verifica o diretório inteiro a cada consulta; foi pensado para pequenos lotes locais.
