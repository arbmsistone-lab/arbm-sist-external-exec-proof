# Etapa 7 — Baseline

Status atual: BLOCKED_BY_STAGE6.

Este diretório contém somente o preflight da baseline. Nenhum modelo é chamado enquanto o M0_QUOTA_PROBE não provar explicitamente:
- status=PASS
- thirty_valid_runs_fit=true
- max_paid_cost_usd=0.00
- auto_paid_upgrade_allowed=false
- billing state conhecido
- model ID exato conhecido

A baseline real, seu prompt, parâmetros, modelo e hash de freeze só serão criados/congelados depois desse gate.
