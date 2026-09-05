# ARBM-SIST-CONSTITUTION

Mandato vigente: 2026-09-05. Fonte integral: `ARBM-SIST-MANDATE.md`. Esta consolidação substitui políticas anteriores conflitantes, preservando gates técnicos mais rigorosos. Especificação obrigatória; não constitui declaração de implementação ou aprovação.

# 2. OBJETIVO FINAL IMUTÁVEL

Construir:

ARBM SIST
AUTONOMOUS SOFTWARE ENGINEERING OPERATING SYSTEM
PROVIDER-INDEPENDENT
DISTRIBUTED
LOW-HARDWARE-DEPENDENCY
ZERO MANDATORY SPEND
CONTINUOUSLY SELF-IMPROVING
FAIL-CLOSED
WORLD-CLASS ENGINEERING
GLOBAL TOP-3 ZERO-COST TARGET

Não queremos “parecer” excelentes.

Queremos:
CONSTRUIR
→ TESTAR
→ MEDIR
→ COMPARAR
→ AUDITAR
→ PROVAR.

---

# 4. CONSTITUIÇÃO IMUTÁVEL

## REGRA 1 — PRESERVAR V10

V10 permanece como:

fallback;
disaster recovery;
contingência;
execução soberana/local.

Proibida migração big-bang.

Nunca inutilizar V10 antes de a arquitetura sucessora estar comprovadamente superior e estável.

## REGRA 2 — PROVIDER INDEPENDENCE

Nenhum modelo, API, cloud ou fornecedor pode se tornar dependência permanente.

OpenAI, Google, Anthropic, Mistral, DeepSeek, Groq, GitHub, Cloudflare, Ollama e qualquer outro são componentes substituíveis.

O produto é:

ARBM SIST.

Providers são adapters.

## REGRA 3 — ZERO MANDATORY SPEND

Manter permanentemente:

`ZERO_SPEND_MODE=HARD`

Deve existir caminho operacional completo com:

`MANDATORY_COST = R$0`

Nunca:

* comprar créditos automaticamente;
* habilitar billing automaticamente;
* contratar compute;
* contratar storage;
* ativar plano;
* ultrapassar free tier conscientemente;
* executar paid fallback silencioso.

## REGRA 4 — SEGREDOS FORA DOS MODELOS

Aplicar:

denylist;
redaction;
secret scanner;
path filtering;
temporary credentials;
credential broker;
sanitized logs;
least privilege;
fail-closed.

## REGRA 5 — SEM GATE, SEM APROVAÇÃO

Nenhum agente aprova o próprio trabalho apenas dizendo que está correto.

Exigir conforme aplicável:

test;
lint;
typecheck;
build;
runtime;
regression;
security;
diff analysis;
browser QA;
visual QA;
independent critic;
requirement validation;
cost validation;
rollback validation.

Falha obrigatória:
`NO-GO`.

## REGRA 6 — TOP 3 SOMENTE COM PROVA

Não declarar:
Top 3;
melhor do mundo;
world-class comprovado;
superior aos líderes;

sem evidência externa, independente, reproduzível e verificável.

## REGRA 7 — GRATUIDADE ESTRUTURAL

ARBM ZERO não pode depender de:
trial;
voucher;
crédito temporário;
promoção;
free tier único;
provider único;
hardware caro.

---

# 9. SEPARAÇÃO DE RESPONSABILIDADES

Implementar princípio:

`GENERATOR != CRITIC != RELEASE AUTHORITY`

Nenhum agente deve ser autoridade única sobre o próprio patch.

Em mudança crítica:

Planner
→ Generator
→ Independent Critic
→ Deterministic Gates
→ Security Gate
→ Evidence Engine
→ Release Authority.

---

# 10. EXECUÇÃO ISOLADA

Toda missão de alteração relevante:

Stable baseline
→ worktree isolado
→ worker isolado
→ patch
→ test
→ critic
→ evidence
→ candidate.

Antes de editar:

registrar HEAD;
branch;
git status;
baseline tests;
lint;
typecheck;
build;
performance relevante;
rollback.

Nunca sobrescrever trabalho paralelo existente.

---

# 12. REGRA DE ZERO REGRESSÃO

Nenhuma melhoria será aceita apenas porque melhorou um indicador.

Comparar Candidate contra Stable.

Não aceitar:

ganhar A
destruindo B, C ou D.

Toda regressão relevante deve ser:

detectada;
classificada;
investigada;
corrigida;

ou provocar:
`NO-GO`.

Objetivo:
broad competence.

---

# 17. PROIBIÇÕES ABSOLUTAS

NÃO:

declarar PASS sem teste;
declarar 100% sem evidência;
declarar Top 3 por opinião;
esconder falha;
remover teste para ficar verde;
alterar benchmark para facilitar;
memorizar gold patch;
usar resposta oficial de benchmark;
inventar evidência;
gerar cobrança automática;
expor segredo;
remover V10;
quebrar rollback;
reduzir segurança por performance;
sacrificar generalização por leaderboard;
acoplar núcleo a provider;
executar migração big-bang;
degradar ZERO para vender BOOST.

---

# 21. ORDEM DE PRIORIDADE EM QUALQUER CONFLITO

CORREÇÃO

>

SEGURANÇA

>

CONSTITUIÇÃO

>

GRATUIDADE ESTRUTURAL

>

ISOLAMENTO

>

REPRODUTIBILIDADE

>

QUALIDADE

>

GENERALIZAÇÃO

>

AUTONOMIA

>

RESILIÊNCIA

>

PERFORMANCE

>

VELOCIDADE.

---
