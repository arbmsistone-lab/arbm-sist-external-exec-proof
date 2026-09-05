# ARBM-SIST-EXECUTION-ROADMAP

Mandato vigente: 2026-09-05. Fonte integral: `ARBM-SIST-MANDATE.md`. Esta consolidação substitui políticas anteriores conflitantes, preservando gates técnicos mais rigorosos. Especificação obrigatória; não constitui declaração de implementação ou aprovação.

# 1. ESTADO INICIAL VERIFICADO

O ponto técnico atual é:

HEAD:
`ae5597e Preserve public precision evidence through context compaction`

P8:
workflow `P8 SWE-rebench V2 real smoke`
run `33939225279`
estado atual: FAILURE.

P9:
workflow `P9 Codex parity release gate`
run `33936250593`
estado atual: FAILURE.

Consequentemente:

P8 NÃO está aprovado.
P9 NÃO está aprovado.
ARBM SIST NÃO está certificado.
ARBM SIST NÃO pode ser declarado 100%.
ARBM SIST NÃO pode ser declarado Top 3.

PRIMEIRA MISSÃO OBRIGATÓRIA:
resolver a causa raiz real do P8.

SEGUNDA:
fechar P9.

NÃO avance para certificação final enquanto P8 e P9 permanecerem vermelhos.

---

# 3. CONGELAR O ROTEIRO NO PRÓPRIO PROJETO

ANTES de ampliar novas frentes, transforme este mandato em Single Source of Truth dentro do repositório.

Criar ou consolidar, em locais adequados à estrutura existente:

1. `ARBM-SIST-CONSTITUTION.md`
2. `ARBM-SIST-PRODUCT-V1-FROZEN.md`
3. `ARBM-SIST-EXECUTION-ROADMAP.md`
4. `ARBM-SIST-RELEASE-GATES.md`
5. `ARBM-SIST-COMMERCIAL-POLICY.md`
6. `ARBM-SIST-INTELLIGENCE-OBSERVATORY.md`
7. policy/configuração machine-readable equivalente à Constituição;
8. testes automatizados que garantam suas invariantes.

Se arquivos equivalentes já existirem, consolide sem criar documentação conflitante.

A Constituição deve existir simultaneamente:

* em documentação;
* em código/policies;
* em testes;
* nos gates de release.

Qualquer tentativa futura de contrariá-la deve gerar:

`CONSTITUTION_VIOLATION`
→ `NO-GO`.

Não altere este roteiro por preferência técnica, moda ou opinião de modelo.

Uma alteração estrutural futura somente poderá ocorrer se:

1. houver problema comprovado;
2. existir alternativa objetivamente superior;
3. houver benchmark/evidência;
4. não houver regressão;
5. rollback estiver preparado;
6. a alteração respeitar a Constituição;
7. a decisão ficar registrada em ADR/evidence bundle.

---

# 11. ORDEM OBRIGATÓRIA DE EXECUÇÃO

Não abrir dezenas de frentes simultaneamente.

## FASE 0

Congelar Constituição, Product Spec, Commercial Policy, Roadmap e Release Gates.

## FASE 1

Resolver P8.

Primeiro:
inspecionar integralmente logs/artifacts do run `33939225279`.

Determinar causa raiz real.

Não realizar tentativa aleatória.

Corrigir a classe da falha.

Executar localmente toda a bateria P8.

Executar smoke externo.

P8 precisa PASS de forma reproduzível.

## FASE 2

Resolver P9.

Inspecionar falha real.

Corrigir.

Executar release gate.

P9 precisa PASS.

## FASE 3

Constitution Engine e anti-regression enforcement.

## FASE 4

ExecutionProvider:
Local;
Remote;
low-RAM independence;
worker isolation.

## FASE 5

Cost Firewall + Free Capability Mesh.

## FASE 6

Intelligence Observatory + Candidate Registry.

## FASE 7

Model Mesh + Frontier Router.

## FASE 8

Context Engine + Memory + Failure Memory + Long-Horizon Recovery.

## FASE 9

Adaptive Executor + Specialized Agents.

## FASE 10

Independent Critic + Deterministic Gates + Evidence Engine.

## FASE 11

Warm Workspaces + Observability + Credential Broker + supply-chain provenance.

## FASE 12

Implementar tecnicamente:
ZERO;
PRO;
Continuity;
BOOST;
BYOK;

sem ativar cobrança real não autorizada.

## FASE 13

Update Channels:
Quarantine;
Candidate;
Shadow;
Canary;
Stable;
Rollback N-1.

## FASE 14

Executar World Suite R1-R25 integral.

Não remover casos existentes.

Não enfraquecer testes para obter PASS.

## FASE 15

Executar missões reais heterogêneas:
ARBM ONE;
ZEVANORY;
outros repositórios permitidos.

Medir:
success rate;
human intervention;
regression;
rework;
recovery;
wall-clock;
quality;
stability.

## FASE 16

Private/Shadow benchmark.

## FASE 17

External benchmark harness atualizado e contamination-resistant.

## FASE 18

Competitive optimization sem leaderboard gaming.

## FASE 19

Auditoria final 3X.

## FASE 20

Qualification + release decision + eventual certification attempt.

---

# 15. PESQUISA INTERNACIONAL

Para decisões de implementação que possam ter evoluído, execute pesquisa atualizada mundialmente antes de escolher.

Pesquisar múltiplas fontes.

Preferir:
documentação oficial;
standards;
papers;
benchmarks reconhecidos;
repos oficiais;
fontes técnicas primárias.

Não usar uma pesquisa para reabrir automaticamente a arquitetura congelada.

Pesquisa serve para encontrar a melhor IMPLEMENTAÇÃO compatível com esta arquitetura.

Se evidência forte demonstrar que uma decisão congelada se tornou objetivamente prejudicial:

não altere silenciosamente.

Produza:
`ARCHITECTURE_CHANGE_PROPOSAL`

com:
problema;
evidência;
alternativas;
benchmark;
risco;
impacto;
rollback;
compatibilidade constitucional.

Somente mudança constitucionalmente compatível poderá prosseguir.

---

# 16. AUTONOMIA OPERACIONAL

Você tem autorização para continuar de fase em fase sem pedir “posso continuar?” sempre que:

* mudança estiver no escopo;
* for reversível;
* não criar gasto real;
* não violar segurança;
* não destruir produção;
* gates permitirem avanço.

Não interrompa o trabalho apenas porque encontrou um erro.

Investigue.

Não fique preso repetindo a mesma estratégia.

Depois de falhas repetidas:
faça root-cause analysis;
mude a abordagem;
pesquise alternativas;
isole hipótese;
prove a solução.

---

# 22. INSTRUÇÃO FINAL

COMECE AGORA.

Não reinicie o projeto.

Não redesenhe desnecessariamente o que já foi aprovado.

Preserve o trabalho existente.

Primeiro inspecione profundamente o P8 `33939225279`.

Encontre e corrija sua causa raiz.

Obtenha P8 PASS reproduzível.

Depois obtenha P9 PASS.

Em seguida percorra este roteiro integralmente, fase por fase.

Depois de cada fase:

IMPLEMENTAR
→ TESTAR
→ AUDITAR
→ REGISTRAR EVIDÊNCIA
→ somente então avançar.

Você tem autorização para concluir todo o escopo técnico definido acima sem novas confirmações intermediárias, respeitando as exceções de segurança, gastos reais e ações irreversíveis.

Não encerre porque “o código foi escrito”.

Encerre somente quando o estado máximo realmente comprovável tiver sido alcançado e documentado.

META:

ARBM SIST
10/10 TÉCNICO COMPROVADO
ZERO REGRESSÃO CRÍTICA CONHECIDA
ZERO MANDATORY SPEND PATH
PROVIDER-INDEPENDENT
SELF-MONITORING
SELF-IMPROVING
FAIL-CLOSED
PRODUCTION-READY

E, somente se a evidência externa realmente permitir:

GLOBAL TOP-3 ZERO-COST CERTIFIED.
