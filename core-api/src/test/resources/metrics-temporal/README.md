# Vetores internos E5b-4

python-canonical-vectors.json contém bytes e hashes gerados por json_bytes Python,
com UTF-8, controles, objetos/listas vazios, ordem Unicode fora do BMP e bigint.

materialized-example é o resultado v2 da prova REAL PostgreSQL E5b-4. O Java lê
somente esses dois arquivos. archive_root dentro do JSON é a identidade histórica
da observação preservada, nunca um caminho consultado, copiado ou remapeado.
Não há dependência desse archive/cluster em checkout novo. Observações locais
atuais não certificam PIT anterior; a garantia conservada é NOT_DEMONSTRATED.
Ledger independente: três jogadas de synthetic-1, soma -1, EPA -1/3; passes 2,
soma -1.123456789012345678901234567890123456789; corrida 1 com soma positiva
0.123456789012345678901234567890123456789; uma jogada com EPA zero observado.
synthetic-6 é COMPLETE vazio em cálculo próprio; synthetic-5 é lacuna de fonte.

zero-mixed-models é vetor SINTÉTICO só do contrato do leitor, produzido por
generate_reader_vectors.py sobre fixtures temporais E5b-3. Conserva somas zero
observadas e modelos v1/v2 separados. Não é transporte/banco nem cálculo de PBP
real; não substitui a prova real. derivedAt tem 29 casas decimais.
