# ARBM-SIST-RELEASE-GATES

Mandato vigente: 2026-09-05. Fonte integral: `ARBM-SIST-MANDATE.md`. Esta consolidação substitui políticas anteriores conflitantes, preservando gates técnicos mais rigorosos. Especificação obrigatória; não constitui declaração de implementação ou aprovação.

# 13. TESTES DE BOOST ANTES DA VENDA

BOOST não deve ser vendido por hipótese.

Executar ZERO × BOOST em tarefas difíceis equivalentes.

Critérios mínimos iniciais:

critical regression:
`0`

managed provider cost:
`<= R$7/customer/month`

success rate difficult tasks:
melhoria relativa alvo `>=10%`

retries/rework:
redução alvo `>=15%`

quota-related unavailability:
redução alvo `>=50%`

recoverable failure success:
melhoria alvo `>=15%`

security:
PASS

privacy:
PASS

cost firewall:
PASS

Se a evidência real não mostrar valor:
NÃO lançar BOOST até corrigir o produto/economia.

---

# 18. AUDITORIA FINAL 3X

Depois de todos os gates técnicos verdes, executar três ciclos independentes completos.

## AUDITORIA A — ENGENHARIA

Architecture
Security
Regression
Performance
Recovery
Provider Independence
Zero-Spend
Secrets
Cost Firewall
Evidence
Supply Chain
Constitution.

## AUDITORIA B — INTELIGÊNCIA

Model routing
Free Capability Mesh
Observatory
benchmark integrity
generalization
long-horizon
critic independence
failure recovery
quality-per-compute
ZERO vs BOOST.

## AUDITORIA C — PRODUTO/ECONOMIA

ZERO
PRO
Continuity
BOOST
BYOK
pricing constants
cost caps
margem
license persistence
cancelamento
upgrade/downgrade
no surprise billing
commercial consistency.

Qualquer falha crítica em qualquer uma:

`NO-GO`.

Corrigir e repetir a auditoria afetada.

---

# 19. DEFINIÇÃO DE “NOTA 10”

“Nota 10” NÃO significa ausência eterna de bugs.

Para este projeto:

NOTA TÉCNICA 10/10 só pode ser declarada quando:

* P8 PASS;
* P9 PASS;
* todos os gates críticos PASS;
* zero regressão crítica conhecida;
* Constitution Suite PASS;
* ZERO path comprovado;
* Cost Firewall PASS;
* recovery PASS;
* rollback PASS;
* security PASS;
* secret isolation PASS;
* provider independence PASS;
* World Suite PASS nos critérios definidos;
* missões reais aprovadas;
* benchmark integrity PASS;
* Evidence Engine completo;
* três auditorias finais PASS.

Ainda assim, separar obrigatoriamente:

TECHNICAL RELEASE:
GO ou NO-GO

WORLD-CLASS READINESS:
VERIFIED ou NOT VERIFIED

GLOBAL TOP-3 ZERO-COST:
CERTIFIED ou NOT CERTIFIED.

Nunca misturar as três.

Top-3 somente com evidência externa suficiente.

---

# 20. RESULTADO FINAL OBRIGATÓRIO

Ao concluir, entregar relatório completo contendo:

baseline original;
HEAD final;
branches;
commits;
PRs;
arquivos alterados;
arquitetura final;
policies;
tests;
lint;
typecheck;
build;
runtime;
security;
regression;
performance;
provider independence;
ZERO cost;
BOOST cost;
secrets;
recovery;
rollback;
World Suite;
missões reais;
benchmarks;
falhas encontradas;
causas raiz;
correções;
riscos residuais;
evidence bundles;
três auditorias finais.

Terminologia final obrigatória:

`PROVADO`
`NÃO PROVADO`
`PENDENTE`
`BLOQUEADO`

Nunca substituir evidência por confiança.

---
