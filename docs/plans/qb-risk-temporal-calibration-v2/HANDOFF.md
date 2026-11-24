# Passagem v2

Resultado: **A — diagnóstico concluído, M3 candidato congelado e avaliação nova pendente**. O sinal é retrospectivo conhecido. Abrir [REPORT](REPORT.md), [DRIFT-AUDIT](DRIFT-AUDIT.md), [MODEL-CARD](MODEL-CARD.md) e [operação/reprodução](README.md).

- Base v1 d654bd65f834f3903006a97b3074123eda26d236 conferida limpa; documentos/código/347 artefatos pinados devem continuar intactos. Site aprovado5b38f04 e servidor18111 preservados. Não confiar em PID histórico.
- Reserva **W9–13**, decidida no commit94e2b82 por exposição agregada W8 na v1. Nunca consultamos novos rótulos dessa reserva. Conhecidos:2024/2025/2026 W1–7. Nenhum desses é holdout novo.
- Configuração científica em `experiment-verified/frozen` no store; arquivos também em evidence/frozen. M3 estrutura2023–24, calibração de intercepto2025, C=.1, offset−0,1593395890. M0/M1 preservados; não reabrir busca ou recalibrar com2026.
- Gate atual bloqueado até no mínimo16/12/2026 01:15 UTC (15/12 às22:15 Fortaleza), sujeito a calendário atualizado e janela completa. Não avaliar parcialmente nem criar automação. `acquire_reserved.py` recusa download prematuro; `reserved.py` valida relógio/manifests/código/contratos/joins antes de abrir rótulos. O recibo OPENED impede segunda abertura pelo mesmo bundle; preservar erro/recibo se houver falha, nunca apagar para tunar.
- Reprodução completa e backup durável verificados conforme recibos do README. Ambiente via lock/wheelhouse; nenhuma dependência em .env ou banco. Modelos são JSON, sem pickle.
-53 QBs identificados e9 outras posições; população mantém62 lançadores. V2 não emite IC comparativo por jogador. Zero eventos e pouco suporte não demonstram habilidade; classificação vem do roster semanal por GSIS, nunca nome.
- A composição comum praticamente não reduz a queda (no suporte principal2022→2025:1,945→1,961p.p.). M1 corrige muito do excesso; M3 agrega LL pooled−0,001449 vsM1 em2024/2025. Fonte/critério FTN e persistência de efeito individual continuam desconhecidos.

Próxima execução autorizável: aquisição pública após maturidade e avaliação integral, **sem mudar o procedimento escolhido**. Revisão técnica humana da v2 não foi presumida. Não houve produção/publicação. Hash de HEAD e commits devem ser lidos de git log; o documento não contém seu próprio hash.
