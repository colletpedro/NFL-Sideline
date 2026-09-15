# Manifesto editorial

`analysis-selections.json` é o único ponto versionado de aprovação para o exportador público. Ele fica fora de
`web-ui/public` e não contém prompts, contexto nem respostas.

Cada item em `selections` deve conter exatamente `gameId`, `analysisCacheId`, `depth` (`FULL`, `BASIC`
ou o modo interno `LEGACY_PUBLISHED`),
`promptHash`, `responseHash`, `status` (`APPROVED`), `reviewedBy`, `reviewedAt` e `asOfDate`. Os hashes são SHA-256
hexadecimais. A aprovação é manual e referencia uma linha imutável existente em `analysis_cache`; editar este
arquivo não gera análises nem altera o banco.

Entradas inválidas ou incompatíveis são omitidas individualmente. Manifesto raiz ausente, ilegível ou inválido
aborta a exportação antes da troca do diretório público; `selections: []` continua válido. Para FULL/BASIC, o
exportador valida a profundidade exata tanto em `asOfDate` quanto no `--as-of` de publicação e rejeita revisão
posterior ao gameday.

### Preservação manual das seis análises Week 1

Em uma sessão posterior, com leitura autorizada do banco, use o snapshot público anterior como fonte de verdade:

1. identifique os seis `gameId` e seus quatro textos/`createdAt` no snapshot anterior;
2. localize, sem alterar nem clonar, a linha legacy `analysis_type=matchup` que produz exatamente esse conteúdo;
3. copie o `prompt_hash` já armazenado, calcule o SHA-256 exato de `response_text` e confira o ID;
4. adicione uma seleção `LEGACY_PUBLISHED` por jogo, com ID e hashes exatos, revisão humana auditável;
5. exporte para diretório temporário com `--as-of`, confirme as seis preservações e só depois siga o runbook.

O seletor aceita esse modo apenas para jogo passado e somente se `createdAt` e os quatro campos públicos forem
idênticos ao snapshot anterior. Legacy não listado, atual ou futuro permanece invisível. O manifesto desta task
fica vazio: nenhuma aprovação real foi inventada. Portanto, não execute o primeiro export contra a saída pública
até concluir e revisar as seis entradas; o procedimento é o gate operacional que impede sua remoção.
