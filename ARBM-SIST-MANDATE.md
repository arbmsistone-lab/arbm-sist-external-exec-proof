# COMANDO MESTRE DEFINITIVO — ARBM SIST

Assuma a responsabilidade técnica integral pela conclusão do ARBM SIST a partir do estado atual e prossiga autonomamente até atingir o máximo estado comprovável definido neste mandato.

Você está AUTORIZADO a investigar, editar, refatorar, criar módulos, testes, adapters, workers, policies, documentação, benchmarks, branches/worktrees isolados, commits, pushes, PRs, pipelines e demais componentes necessários dentro do projeto ARBM SIST.

NÃO espere nova autorização entre etapas técnicas reversíveis e pertencentes ao escopo deste projeto.

Quando um gate falhar, não pare apenas para relatar o problema: investigue a causa raiz, corrija-a de forma isolada, execute novamente toda a bateria necessária e continue somente quando a evidência permitir.

Exceções que continuam exigindo autorização humana explícita:

* qualquer gasto real novo;
* ativação de billing;
* contratação de plano/serviço;
* alteração destrutiva de produção;
* exclusão irrecuperável de dados;
* exposição ou rotação de credenciais sensíveis fora de política;
* mudança jurídica/comercial não prevista neste mandato.

---

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

# 5. ARQUITETURA DE PRODUTO CONGELADA

## ARBM ZERO

Preço:
`R$0`

Objetivo:
oferecer um dos melhores motores gratuitos de engenharia de software que conseguirmos comprovar.

Não degradar propositalmente a inteligência do ZERO apenas para vender upgrade.

ZERO deverá utilizar:

Free Capability Mesh;
Model Mesh;
providers gratuitos homologados;
open models;
execução local;
fallback soberano;
Frontier Router;
Cost Firewall;
ferramentas;
terminal;
Git;
testes;
build;
recovery permitido.

## ARBM PRO

Preço oficial de aquisição:
`R$1.197,00`

Inclui:

* licença Stable adquirida;
* recursos avançados;
* ARBM ZERO Engine;
* 12 meses de Continuity & Intelligence.

A versão Stable adquirida permanece utilizável pelo titular mesmo após eventual cancelamento do Continuity, observadas as condições técnicas e de segurança da versão.

## CONTINUITY & INTELLIGENCE

Preço:
`R$79,90/mês`

Primeira cobrança:
somente a partir do mês 13 após aquisição PRO.

Função:

* atualizações Stable;
* evolução do sistema;
* novos adapters;
* segurança;
* novos providers homologados;
* Model Registry;
* benchmarks;
* Intelligence Observatory;
* melhorias do Router;
* melhorias do Executor;
* compatibilidade;
* documentação;
* suporte previsto pelo produto.

Não representa franquia de tokens premium.

## ARBM BOOST

Preço-alvo:
`R$19,90/mês`

Opcional.

Objetivo:
Managed Premium Intelligence.

Regra econômica inicial:

`MAX_MANAGED_AI_COGS_PER_CUSTOMER = R$7.00/mês`

Não é obrigação gastar R$7.

É teto máximo.

ZERO deve resolver primeiro.

BOOST será utilizado apenas quando houver expectativa verificável de ganho em:
qualidade;
recuperação;
latência;
disponibilidade;
critic;
planning;
debugging;
tarefa complexa.

Nunca oferecer premium ilimitado.

Ao atingir orçamento:
`BOOST_BUDGET_EXHAUSTED`
→ retornar ao ZERO.

Nunca:
→ cobrar overage automaticamente.

O BOOST somente poderá ser lançado comercialmente depois de A/B real comprovar ganho suficiente e economia sustentável.

## BYOK

Incluído.

Usuário pode conectar provider próprio.

Cobrança:
cliente ↔ provider.

ARBM aplica Cost Firewall e orçamento configurado pelo cliente.

---

# 6. INTELLIGENCE OBSERVATORY NATIVO

A monitoração mundial NÃO depende de ChatGPT, Codex externo ou operador humano permanente.

Construir:

`ARBM INTELLIGENCE OBSERVATORY`

Ele pertence ao próprio ARBM SIST.

Responsabilidades:

descobrir continuamente:

* novos modelos;
* modelos open-weight;
* providers;
* APIs;
* free tiers;
* preços;
* quotas;
* limites;
* ferramentas de desenvolvimento;
* MCPs;
* runtimes;
* computer use;
* browser agents;
* coding agents;
* técnicas de context engineering;
* compression;
* caching;
* inference;
* segurança;
* CVEs;
* mudanças de privacidade;
* mudanças de termos;
* benchmarks;
* novas arquiteturas de agentes.

Pipeline obrigatório:

DISCOVER
→ COLLECT
→ VERIFY
→ NORMALIZE
→ CANDIDATE
→ SECURITY CHECK
→ COST CHECK
→ PRIVACY CHECK
→ BENCHMARK
→ SHADOW
→ CANARY
→ STABLE ou REJECT
→ MONITOR
→ LEARN.

Jamais:

`NEW → STABLE`.

O Observatory pode descobrir e testar autonomamente.

Não pode violar Constituição, segurança, custo ou política comercial.

---

# 7. HIERARQUIA DEFINITIVA DE INTELIGÊNCIA

Executar da forma mais econômica capaz de preservar qualidade:

NÍVEL 0
Determinístico / sem LLM quando possível.

NÍVEL 1
ARBM ZERO.

NÍVEL 2
Premium Efficient.

NÍVEL 3
Premium Strong.

NÍVEL 4
Frontier Burst.

NÍVEL 5
BYOK ou autorização humana quando necessário.

Nunca usar frontier indiscriminadamente.

Objetivo:

`MAX VERIFIED QUALITY / COST / COMPUTE / TIME`

Não reduzir qualidade apenas para economizar.

Não desperdiçar modelos caros em tarefas que modelos gratuitos/econômicos resolvem igualmente bem.

---

# 8. FRONTIER ROUTER

O Router deve escolher dinamicamente:

provider;
worker;
modelo;
contexto;
estratégia;
tools;
critic;
parallelism;
repair policy.

Considerar:

task type;
risk;
language;
repository;
historical success;
model quality;
provider health;
latency;
capacity;
context requirement;
previous failures;
free quota;
reliability;
privacy;
security;
cost;
ZERO_SPEND_MODE;
quality-per-compute.

Registrar resultados reais de cada missão.

Aprender com outcomes.

Não memorizar respostas de benchmark.

Aprender classes de problema.

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

# 14. SUPPLY CHAIN

Release Stable deve registrar conforme viabilidade:

commit;
hash;
builder;
dependencies;
SBOM;
provenance;
test evidence;
policy result;
signature/attestation.

Objetivo:
provenance verificável e build reproduzível.

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
