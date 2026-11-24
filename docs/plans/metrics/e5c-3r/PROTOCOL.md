# E5c-3R — protocolo anterior à carga

Base exata: ce06a6291d1a2e935871fef04f543a54489755f5. Branch isolada
codex/metrics-real-recovery-e5c3r. Checkout original preservado, inclusive seus
arquivos históricos não rastreados. Sem merge, push, deploy ou aquisição.

Escopo fechado: os quatro Parquets nominais 2025/2026 informados na solicitação.
Conferir hashes antes/depois; copiar byte a byte, sem modificar originais.
Inventário registra schema, linhas, participantes, fases/semanas e hashes.
Destinos novos sob editorial/local-artifacts/real-recovery/<UUID> e
editorial/local-artifacts/backups/<UUID> do checkout original, fora de web-ui.
Operações/credenciais e PGDATA ficam em raiz separada, fora do Git/distribuição.
Reserva de 2 GiB livres; estimativa preventiva <= 1 GiB para duas cópias dos
artefatos (~15 MB de fontes, materialização e bundle com linhagem duplicada),
mais cluster vazio próprio. Nenhuma remoção para ganhar espaço.

O runtime nativo temporário antigo desapareceu. Há Docker ativo e imagem local
PostgreSQL 17.6 (ID completo registrado no preflight). Usar --pull never,
entrypoint próprio/initdb vazio, nome/label UUID, volume novo e publicação somente
127.0.0.1 em porta livre. Não iniciar serviço global, usar entrypoint Supabase,
reutilizar container/cluster existente ou acessar banco remoto. Relay BusyBox nc
já presente na imagem liga a porta publicada ao PostgreSQL em loopback interno;
o servidor real conserva host/porta exatos exigidos pelo guard aceito. Não mudar
o guard. Login de domínio e writer separados, não administrativos, mesmas grants,
RLS, marker e restrições dos harnesses E5b-2/5/6. Aplicar apenas as três migrations
versionadas necessárias (baseline, hardening e persistência). Administração só
pelo socket Unix do próprio container.

Antes de escrever no banco: conferir código aceito contra a base e planejar pelo
pipeline aceito; reconciliar todos os audits/grupos pelo auditor E5b-6 independente.
Alvos, autorizados somente após igualdade dos quatro hashes: REG2025 272/32813,
POST2025 13/1689, REG2026 32/3830. Quantidade não demonstra completude.
Depois: pipeline local skip-acquire, SQL, idempotência, extração integral nominal,
recover/materialize/publish/read aceitos (v2/input-v3), com derivedAt real atual.
Não inventar receipts ou persisted_at antigos. Capturar relações e snapshot SQL
antes de parar o cluster. Não é necessário executar PIT/Java vazio novamente:
números vêm das somas reconciliadas e reader E5c-2, nunca de PIT vazio.

Solicitação nova com a mesma coorte E5c-2: BAL/DAL REG2026 W1, W2, W1–2;
NE POST2025 separado; BAL W3 ausente. Ataque/defesa e três fundamentos.
Associações novas nominais; derivedAt atual. Não editar real_proof.py nem seu
relatório. Conferir frações, denominadores, participantes, período e UNKNOWN;
comparar valores com o extrato histórico sem aceitar o extrato como fonte.
Tabela histórica/nova distingue cálculo/conteúdo de receipts/archive/derivação.

Preservação: fontes, artifacts, archive, journals, extração completa, snapshot,
materialização completa, solicitação, bundle, inventários e manifestos. Manifesto
SHA-256 de todos os arquivos; segunda cópia byte a byte, sem symlinks. Verificar
hashes e leitura pública integral da cópia com a primeira localização indisponível
(renomeação temporária somente dos novos diretórios, nunca histórico). Duas cópias
no mesmo disco não são recuperação de desastre. Grandes artefatos fora do Git.

Laboratório: REAL_ARCHIVE, path durável e pin novo conferido. Reader → DTO → sessão
Vite → HTTP real de todos os documentos; desktop/mobile/teclado/details, escolha,
reload e reinício/revalidação. Sem redesign/comparação/pregame. Falhas somente em
cópias descartáveis: adulteração com rehash externo, dependência ausente, pin
errado, extrato, campo/limitação obrigatórios e sessão antiga após reinício.
O reinício deve mudar conteúdo da sessão para o teste 409; reinício idêntico pode
legitimamente conservar sessionId. Preservar cópias reais e manifests intactos.

Testes pertinentes uma vez; sem mudar gates históricos ou componentes aceitos.
Completude, expectativa, modelo EPA, disponibilidade/ingestão histórica e fim de
evento continuam UNKNOWN. Sem participantes: compreensão humana não avaliada.
Finally encerra somente PG/container/Vite/Chrome próprios; confirma PID/listener
inexistentes e portas livres. Dados e logs preservados mesmo em falha. Se faltar
runtime/permissão, registrar bloqueio específico e concluir checks independentes.
