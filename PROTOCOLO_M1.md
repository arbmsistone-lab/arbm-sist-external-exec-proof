# PROTOCOLO M1 — ARBM SIST

Status: protocolo fechado para o MARCO_1 exploratório.

## Objetivo
Medir se uma arquitetura futura do ARBM SIST executa tarefas inéditas no LibreOffice Calc melhor que uma baseline simples, sem respostas, coordenadas, branches ou scripts específicos por tarefa.

O M1 não certifica classe mundial, top 3, autonomia geral, causalidade, self-repair ou produto completo.

## Regra superior
Nenhuma capacidade autônoma pode ser declarada por cenário hardcoded. Somente tarefas inéditas, lacradas antes do desenvolvimento do agente, contam como evidência.

## Aplicativo e escopo
Aplicativo: LibreOffice Calc.
Sistema: Windows.
Idioma: pt-BR.
Formato principal: ODS.

Operações permitidas no M1: ler/editar células, inserir/excluir linhas e colunas, criar/renomear/excluir abas, copiar/mover intervalos, ordenar/filtrar tabela simples, inserir fórmula simples, formatação básica e salvar o documento.

Fora do M1: macros/VBA/Basic, fontes externas, banco, gráficos, imagens, PDF, e-mail, navegador, internet, arquivos protegidos, colaboração, UNO no agente/baseline, edição direta de ODS no agente/baseline, OCR externo, fórmulas complexas, multiaplicativo, recovery, self-repair, multi-agent e process mining.
## Tarefas secretas
Serão 5 tarefas criadas pelo usuário fora do repositório e fora dos chats de desenvolvimento.
Cada tarefa é de uso único como prova, usa verificadores genéricos pré-existentes, recebe HUMAN_ORACLE=PASS antes do lacre, nonce aleatório e commitment SHA-256 antes do desenvolvimento do agente.

## Verificação independente
O agente não decide o resultado.
O evaluator roda depois da execução.
FALSE_SUCCESS_CLAIM ocorre quando AGENT_CLAIM=SUCCESS e INDEPENDENT_VERIFIER=FAIL.

## Integridade
A comparação é semântica, não byte a byte.
Avalia valores, textos, fórmulas normalizadas, nomes/ordem de abas, conteúdo e ordem relevante de linhas, formatos numéricos relevantes, filtros, nome e formato do arquivo.
Ignora metadados, editor, timestamp, seleção, célula ativa, scroll, zoom, geometria de janela, largura de coluna, altura de linha e configurações de visualização, salvo quando forem objeto explícito da tarefa.

PASS exige TARGET_VERIFIER=PASS, UNEXPECTED_MUTATIONS=0, OUTPUT_PATH=EXPECTED e OUTPUT_FORMAT=EXPECTED.

## Normalização pt-BR
Verificadores devem normalizar nomes de função, separador decimal, separador de argumentos, referências absolutas/relativas, whitespace e case irrelevante.

## Human oracle
Todo verificador genérico deve ter teste positivo e negativo.
Toda tarefa secreta deve passar por execução manual do usuário e pelo evaluator antes do lacre.
## Isolamento
Agent recebe somente instruction, arquivo de trabalho, screenshots e ações de mouse/teclado/tela.
Não pode ler verifier, evaluator, tarefa secreta, fixture original ou expected state.
Runner controla tempo, passos, chamadas e watchdog, mas não decide PASS/FAIL.
Evaluator roda depois e pode usar bibliotecas de ODS.

Auditoria estática aplica-se somente a agent/ e baseline/, procurando IDs secretos, branches por tarefa, UNO, odfpy/openpyxl/ZIP/XML usados para manipular o alvo, caminhos secretos/verifiers e coordenadas fixas específicas.

## Limites
Cada tarefa fixa antes da prova: max_agent_steps, max_wall_time_seconds, max_model_calls e max_paid_cost_usd=0.00.
Estourar limite é FAIL.

## Falhas
PERCEPTION, PLANNING, ACTION, VERIFICATION ou ENVIRONMENT.

BENCHMARK_INVALID tem lista fechada: bug comprovado do runner, reset divergente por hash, bug comprovado evaluator/verifier, watchdog antes do limite, falha comprovada de screenshot/controle, reinício/desligamento da máquina, fixture secreta não disponibilizada conforme protocolo ou corrupção comprovada do log necessário.
Exige evidência objetiva.
Máximo de 2 repetições por slot.
Se mais de 20% dos slots forem inválidos, a rodada inteira é inválida.
## Baseline
Prompt e código congelados antes do agente ARBM SIST.
No dry run deve resolver pelo menos 1 tarefa de desenvolvimento.
Hash da baseline entra no lacre e ela não muda durante a rodada.
Baseline e ARBM recebem mesmo modelo, versão/ID quando verificável, temperatura, resolução, max output, chamadas, tempo e ações.

## Desenho experimental
5 tarefas secretas x 3 repetições x 2 sistemas = 30 execuções válidas máximas.
Execuções pareadas por task/repetition; ordem BASELINE/ARBM sorteada antes.
Registrar RANDOMIZATION_SEED e RUN_ORDER_SHA256.
M1 é exploratório e não produz rótulo global PASS/FAIL/CERTIFIED/WORLD_CLASS.

ARBM_ARCHITECTURE_SHOWED_ADVANTAGE=true somente se:
1. vencer em >=3 das 5 tarefas;
2. não perder nenhuma tarefa por diferença >1 execução;
3. FALSE_SUCCESS_RATE <= baseline;
4. total de sucessos ARBM > baseline.
SMALL_SAMPLE=true e STATISTICAL_SIGNIFICANCE_NOT_CLAIMED=true.

## Ordem de implementação
1. Reset de fixture + fingerprint.
2. Biblioteca de verificadores.
3. Integrity checker.
4. Human oracle.
5. Runner + limites/watchdog.
6. M0_QUOTA_PROBE.
7. Baseline.
8. Dry run em 2-3 tarefas de desenvolvimento.
9. Congelar infraestrutura/verificadores/escopo/baseline.
10. Criar e lacrar 5 tarefas secretas.
11. Só então desenvolver o agente ARBM SIST.
## Gate da Etapa 1
A Etapa 2 não começa sem execução local no Windows produzindo:
- MUTATION_DETECTED_10/10
- RESET_RESTORED_10/10
- METADATA_IGNORED=PASS
- NUMERIC_TYPE_DISTINGUISHED=PASS
- FINGERPRINT_STABLE=PASS
- ETAPA_1_LOCAL_TEST_COMPLETE

O reset real deve, em cada rodada: restaurar a fixture, aplicar mutação semântica, provar hash diferente, executar reset e provar retorno ao hash original.
As mutações cobrem valor, texto, linha nova, linha excluída, aba nova e aba renomeada.
O teste de metadados prova que alterações não semânticas não mudam o hash.
O teste numérico prova que 10 numérico e "10" texto produzem estados semânticos diferentes.
O fingerprint é executado duas vezes e comparado ignorando apenas horários.

## Modo de execução em segundo plano
Por autorização do usuário em 2026-10-01, a Etapa 1 pode criar a fixture via LibreOffice headless para não roubar foreground.
Isso não é prova de automação GUI e não deve ser usado como evidência de capacidade visual do ARBM SIST.
A criação headless é apenas preparação determinística da fixture para validar reset, hash semântico e fingerprint.

A Etapa 2 permanece bloqueada até decisão explícita após revisão da Etapa 1.


## Resultado da Etapa 2 — biblioteca de verificadores
Executado localmente no Windows em 2026-10-01, em segundo plano.

Cobertura validada:
- cell_value / cell_text / cell_value_by_row_label
- row_exists / row_not_exists / row_count / row_matches
- row_inserted / row_deleted
- column_exists / column_not_exists / column_values / column_order
- column_inserted / column_deleted
- sheet_exists / sheet_not_exists / sheet_count / sheet_order / sheet_renamed
- formula_in_cell / formula_pattern / formula_result
- range_sorted_ascending / range_sorted_descending
- range_copied / range_moved
- filter_active / filter_condition / visible_rows_match
- normalização pt-BR de fórmula e número

Gate observado:
- VERIFIER_CASES=42/42
- FALSE_POSITIVES=0
- FALSE_NEGATIVES=0
- NORMALIZE_PTBR_FORMULA=PASS
- NORMALIZE_PTBR_NUMBER=PASS
- STAGE2_VERIFIER_GATE=PASS

A primeira rodada da Etapa 2 falhou em formula_pos e NORMALIZE_PTBR_FORMULA. A causa foi normalização incompleta da referência ODF `[.B2:.B3]`; o bug foi corrigido antes do gate final. Essa falha inicial não foi ocultada nem usada como PASS.

A Etapa 3 permanece bloqueada até o registro/versionamento deste gate.


## Resultado da Etapa 3 — Integrity Checker
Executado localmente no Windows em 2026-10-01, em segundo plano.

O Integrity Checker compara semanticamente o documento final com o estado esperado e só aprova quando:
- TARGET_VERIFIER=PASS
- UNEXPECTED_MUTATIONS=0
- OUTPUT_PATH=PASS
- OUTPUT_FORMAT=PASS

Casos legais aceitos:
- edição correta da célula-alvo
- ordenação correta
- inserção correta de linha
- exclusão correta de linha
- cópia correta de intervalo
- movimentação correta de intervalo
- ruído somente de metadados
- alteração somente de autor/data/estado de visualização/posição de cursor

Falhas injetadas detectadas:
- outra célula alterada
- aba apagada
- linha extra
- fórmula perdida
- target verifier em FAIL
- nome/caminho de saída errado
- arquivo não ODS disfarçado com extensão .ods

Gate observado:
- LEGAL_MUTATIONS_ACCEPTED=8/8
- INJECTED_SIDE_EFFECTS_DETECTED=7/7
- FALSE_POSITIVES=0
- FALSE_NEGATIVES=0
- STAGE3_INTEGRITY_GATE=PASS

O comparador semântico ignora metadados e estado de visualização, mas preserva como relevantes valores, textos, fórmulas, tipo, estilo, repetição de células, nomes e estrutura de abas/linhas/células.

A Etapa 4 permanece bloqueada até o registro/versionamento deste gate.


## Resultado da Etapa 4 — Human Oracle Mode
Executado localmente no Windows em 2026-10-01, em segundo plano.

A infraestrutura de Human Oracle foi implementada e testada com casos de desenvolvimento marcados explicitamente como DEVELOPMENT_ONLY.

Um oracle só pode produzir oracle_pass=true quando TODAS as condições forem verdadeiras:
- human_completed=true
- operator_confirmation=I_COMPLETED_THIS_TASK_MANUALLY
- hash da fixture igual ao hash atestado
- hash da saída igual ao hash atestado
- todos os verificadores independentes PASS
- Integrity Checker PASS

Casos de infraestrutura testados:
- atestação de desenvolvimento válida -> PASS
- ausência de confirmação humana -> FAIL
- hash da fixture divergente -> FAIL
- saída incorreta -> FAIL

Gate observado:
- ORACLE_CASES=4/4
- FALSE_POSITIVES=0
- FALSE_NEGATIVES=0
- STAGE4_ORACLE_INFRA_GATE=PASS
- SECRET_HUMAN_ORACLE_STATUS=PENDING_SECRET_TASK_CREATION

Importante: o caso positivo usado nesta etapa é somente um artefato de teste DEVELOPMENT_ONLY. Ele não constitui prova de que uma pessoa executou uma futura tarefa secreta. Nenhuma tarefa secreta existe neste momento e, portanto, nenhuma recebe HUMAN_ORACLE=PASS agora.

Quando as 5 tarefas secretas forem criadas, cada uma deverá ser executada manualmente pelo usuário no Calc, validada pelo verifier + Integrity Checker e atestada antes do nonce/commitment final.

A Etapa 5 pode iniciar porque o mecanismo Human Oracle está pronto; o gate humano das tarefas secretas permanece obrigatoriamente futuro.


## Resultado da Etapa 5 — Runner + Watchdog
Executado localmente no Windows em 2026-10-01, em segundo plano.

Limites implementados e testados:
- max_agent_steps
- max_wall_time_seconds
- max_model_calls
- max_paid_cost_usd=0.00

Casos observados:
- execução normal -> PASS
- excesso de passos -> FAIL / ACTION / LIMIT_AGENT_STEPS
- excesso de model calls -> FAIL / PLANNING / LIMIT_MODEL_CALLS
- custo pago > 0 -> FAIL / ENVIRONMENT / PAID_COST_FORBIDDEN
- wall time atingido no limite configurado -> FAIL / ENVIRONMENT / LIMIT_WALL_TIME
- watchdog antes do wall limit -> BENCHMARK_INVALID / WATCHDOG_BEFORE_CONFIGURED_LIMIT
- falha comprovada de screenshot/controle -> BENCHMARK_INVALID / SCREENSHOT_CONTROL_FAILURE
- corrupção do log necessário -> BENCHMARK_INVALID / REQUIRED_LOG_CORRUPTION
- verifier independente falhou -> FAIL / VERIFICATION / INDEPENDENT_VERIFIER_FAIL
- reset divergente por hash -> BENCHMARK_INVALID / RESET_DIVERGENCE

Gate observado:
- RUNNER_CASES=10/10
- LIMIT_EXCEED_CLASSIFIED_AS_FAIL=PASS
- CLOSED_INVALID_LIST_ENFORCED=PASS
- MAX_PAID_COST_USD_ZERO_ENFORCED=PASS
- STAGE5_RUNNER_WATCHDOG_GATE=PASS

Política de rodada validada:
- 20% exatos de slots inválidos não invalida a rodada
- incidência >20% invalida a rodada
- no máximo 2 repetições após um slot inicialmente inválido
- terceira repetição adicional é rejeitada

Gate da política:
- ROUND_POLICY_CASES=4/4
- INVALID_THRESHOLD_GT_20_PERCENT=PASS
- MAX_2_INVALID_REPEATS_PER_SLOT=PASS
- STAGE5_ROUND_POLICY_GATE=PASS

Nenhum modelo pago foi chamado nesta etapa; os testes usam dummy agents locais.

A Etapa 6 (M0_QUOTA_PROBE) permanece bloqueada até o registro/versionamento deste gate.


## Resultado parcial da Etapa 6 — M0_QUOTA_PROBE
Executado em 2026-10-01, em segundo plano e sem chamada paga.

Estado público atual confirmado por documentação oficial do Gemini API:
- provedor alvo: Google Gemini Developer API / Google AI Studio
- modelos atuais recomendados para novos projetos incluem gemini-3.8-flash e gemini-3.5-flash-lite
- limites ativos de RPM/TPM/RPD são específicos do projeto/modelo e devem ser consultados no Google AI Studio
- Free Tier e Paid Tier dependem do estado de billing/tier do projeto
- upgrade automático para uso pago é proibido neste protocolo

Estado real observado na máquina:
- gcloud_installed=false
- nenhuma variável GOOGLE/GEMINI/GENAI/VERTEX/GCLOUD detectada
- Chrome instalado, mas sem porta CDP/debug ativa
- nenhuma credencial de API Gemini detectada por variável de ambiente
- account_project_id=UNKNOWN
- account_exact_model_id=UNKNOWN
- account_usage_tier=UNKNOWN
- account_active_rpm/tpm/rpd=UNKNOWN
- account_billing_state=UNKNOWN
- free_tier_confirmed_for_account=false
- thirty_valid_runs_fit=UNKNOWN
- max_paid_cost_usd=0.00
- auto_paid_upgrade_allowed=false

Status:
M0_QUOTA_PROBE=BLOCKED_ACCOUNT_SPECIFIC_STATE_NOT_OBSERVED

Este bloqueio não é substituído por limites públicos genéricos. A Etapa 7 (Baseline) NÃO pode iniciar até observar no projeto real:
1. projeto/conta usados no AI Studio;
2. modelo visível e ID exato;
3. tier ativo;
4. limites ativos RPM/TPM/RPD;
5. billing state;
6. confirmação de que 30 execuções válidas cabem sem custo pago.

Nenhuma tentativa de vincular billing, adicionar crédito ou migrar para tier pago é autorizada.


## Preparação pré-Etapa 7/8 — infraestrutura sem modelo
Executado em 2026-10-01, em segundo plano, sem chamada de modelo e sem custo pago.

Artefatos preparados:
- baseline_config.template.json
- baseline_agent.py com fail-closed se config/modelo/freeze não estiverem definidos
- baseline_prompt.template.md
- dry_run_harness.py
- dummy_adapter.py
- 3 tarefas DEVELOPMENT_ONLY para teste do harness
- generate_manifest.py / verify_pre_freeze.py
- generate_order.py / verify_order.py

Resultados locais:
- baseline sem config -> bloqueada corretamente
- DRY_RUN_HARNESS_CASES=3/3
- STAGE8_HARNESS_PREP=PASS
- MODEL_CALLS_EXECUTED=0
- PAID_COST_USD=0.00
- TOTAL_SLOTS=30
- PAIR_BALANCE=PASS
- RANDOMIZATION_VERIFY=PASS
- RUN_ORDER_FILE_REPRODUCIBLE=true
- PRE_FREEZE_FILES=13
- PRE_FREEZE_HASH_ERRORS=0
- PRE_FREEZE_MANIFEST=PASS

Randomização pré-registrada:
- RANDOMIZATION_SEED=20261001
- RUN_ORDER_SHA256=0c0f9c35906b07534e2f61c8e9367a5c13897339a164033112dd660cc43cc62e
- RUN_ORDER_FILE_SHA256=c5c4fa78dbcb1a255002e5734ebe3c6b6c3de3a258c474000016e63c62788082

Manifesto pré-freeze:
- PRE_FREEZE_MANIFEST_SHA256=58349d5a0130e2c9351d9851c2663869f65329aafeb9cb53b43d8163efd9cf8f
- status=PRE_FREEZE_ONLY

Nenhum destes hashes constitui o freeze final da baseline. O freeze final só pode ocorrer depois de:
1. M0_QUOTA_PROBE=PASS;
2. modelo exato e billing/tier conhecidos;
3. baseline configurada;
4. baseline resolver >=1 tarefa de desenvolvimento no dry run real;
5. parâmetros finais congelados.

ETAPA_7_BASELINE continua NOT_RUN.
ETAPA_8_DRY_RUN_REAL continua NOT_RUN.


## Etapa 6 — estado específico da conta AI Studio observado
Inspeção visível somente leitura executada em 2026-10-01.

Projeto selecionado:
- display_name=ARBM-SIST-G3-PAID-CERT
- project_id=arbm-sist-g3-paid-cert

Modelo:
- visible_name=Gemini 3.5 Flash
- exact_model_id=gemini-3.5-flash

Tier e limites ativos observados no AI Studio:
- usage_tier=Tier 1
- RPM=1000
- TPM=2000000
- RPD=10000

Máximo de uso observado nos últimos 28 dias:
- RPM=18
- TPM=401470
- RPD=388

Billing:
- billing_account=My Billing Account
- plan=Tier 1 / prepay
- status=prepaid credits exhausted
- current project spend shown=R$0,00
- service banner states prepaid credits are exhausted and more credits are required to resume service
- free_tier_confirmed_for_account=false
- auto_paid_upgrade_allowed=false
- max_paid_cost_usd=0.00

Conclusão operacional:
- rate limits themselves are sufficient for 30 valid runs
- current billing state prevents API execution because prepaid credit balance is exhausted
- thirty_valid_runs_fit_without_paid=false
- M0_QUOTA_PROBE=BLOCKED_NO_PREPAID_CREDITS
- Stage 7 baseline remains NOT_RUN


## Provider probe adicional — Groq
Executado em 2026-10-01.

Conta GroqCloud autenticada:
- organization=Personal
- project=Default Project
- plan=Free / no Dev Plan observed
- dedicated key ARBM-SIST-M1-BENCHMARK exists in console
- local secret file present and not committed

API probe:
- GET /openai/v1/models -> HTTP 403 Forbidden
- authentication secret shape is present locally
- Groq docs classify 403 as permission restriction, not missing credentials

Console probe:
- /settings/organization -> internal error
- /settings/limits -> internal error
- /settings/project/limits -> internal error
- /playground -> internal error

Conclusion:
- GROQ_PROVIDER_STATUS=BLOCKED_ACCOUNT_OR_ORG_PERMISSION
- GROQ_KEY_INVALID_NOT_PROVEN
- GROQ_MODEL_PERMISSION_EDIT=UNAVAILABLE_DUE_CONSOLE_ERROR
- PAID_UPGRADE_NOT_USED
- BILLING_CHANGE=NONE
- MODEL_CALLS_SUCCESSFUL=0

Next provider candidate:
- OpenRouter Free
- fixed multimodal model candidate=qwen/qwen3.8-27b:free
- max_paid_cost_usd=0.00


## Etapa 6 — M0_QUOTA_PROBE fechado com OpenRouter
Executado em 2026-10-01.

Provider final do M1:
- provider=OpenRouter
- account_plan=Free
- access_mode=authenticated_web_chat_session
- workspace=Personal/default
- exact_model_id=qwen/qwen3.8-27b:free
- model_name=Qwen3.8 27B (free)
- input=text,image,video
- output=text
- tool_calling=true
- prompt_price_usd_per_million=0
- completion_price_usd_per_million=0

Runtime proof:
- active model shown in OpenRouter chat=Qwen3.8 27B (gratuito)
- prompt=Responda exatamente: M1_PROVIDER_OK
- observed response=M1_PROVIDER_OK
- runtime_probe=PASS

Free quota planning:
- free_requests_per_day=50
- max_model_calls_per_run=8
- 30 valid runs worst-case calls=240
- maximum allowed invalid slots at 20%=6
- maximum extra invalid attempts for a still-valid round=12
- conservative dry-run slots=6
- conservative worst-case total requests=384
- minimum calendar days at 50/day=8
- benchmark key validity=30 days
- thirty_valid_runs_fit=true, provided quota pacing across days is respected

Cost safeguards:
- max_paid_cost_usd=0.00
- auto_paid_upgrade_allowed=false
- target model is explicitly the :free variant
- dedicated OpenRouter key was created with custom credit limit USD 0 and 30-day validity
- runtime proof used authenticated web chat and did not expose/read the secret

M0_QUOTA_PROBE=PASS

Stage 7 preflight result:
- M0_STATUS_PASS=PASS
- RUNTIME_PROBE_PASS=PASS
- THIRTY_RUNS_FIT=PASS
- MAX_PAID_COST_ZERO=PASS
- AUTO_PAID_DISABLED=PASS
- BILLING_STATE_KNOWN=PASS
- MODEL_ID_KNOWN=PASS
- MODEL_PRICE_ZERO=PASS
- BASELINE_PREFLIGHT=PASS

Stage 7 baseline remains NOT_RUN until the generic baseline implementation completes a real development dry run.


## DEV01_RUN1 interruption classification
- DEV01_RUN1=BENCHMARK_INVALID
- cause=CONTROL_CHANNEL_DISCONNECTED
- last_confirmed_control_channel_communication=2026-10-01T16:14:58-03:00
- PID 14292 was not running after reconnect
- events.json absent
- agent_result.json absent
- wall-time enforcement during the disconnected interval was not provable
- metric_inclusion=false
- forensic copy preserved at stage7/dev_runs/dev01_invalid_run1
- original DEV01 run discarded and reset before any repeat

## Connection-independent runner hardening
The baseline execution path now uses a detached local wrapper and watchdog:
- stage7/launch_detached.ps1
- stage7/detached_watchdog.ps1
- stage7/launch_baseline_detached.ps1
- stage7/run_baseline_child.ps1
The watchdog writes local state/heartbeat/final logs and enforces max_wall_time_seconds independently of Desktop Commander. Timeout termination uses taskkill /T /F to terminate the child process tree.

Forced disconnect test without AI:
- test child started=2026-10-01T16:22:33.9865478-03:00
- Desktop Commander intentionally shut down=2026-10-01T16:22:46.763-03:00
- child ended=2026-10-01T16:23:14.5955180-03:00
- watchdog final=2026-10-01T16:23:15.0965797-03:00
- elapsed_seconds=42.394
- NO_AI_CHILD=PASS
- ai_calls=0
- watchdog_enforced=true
- remote channel reconnected automatically after the child had continued locally

## Frozen shared model contract
MODEL_CONTRACT=ARBM_SIST_M1_SHARED_MODEL_V1
MODEL_CONTRACT_FROZEN=true
PROVIDER=OpenRouter
EXECUTION_LOCATION=remote free inference via authenticated OpenRouter web session
MODEL_ID=qwen/qwen3.8-27b:free
MODEL_NAME=Qwen3.8 27B (free)
TEMPERATURE=0
MAX_OUTPUT_TOKENS=2048
MAX_AGENT_STEPS=40
MAX_WALL_TIME_SECONDS=180
MAX_MODEL_CALLS=8
MAX_PAID_COST_USD=0.00
SCREENSHOT=1536x864
LOCALE=pt-BR
FREE_REQUESTS_PER_DAY=50
QUOTA_PACING_REQUIRED=true

The exact same shared model contract applies to baseline and ARBM SIST agent. No model/provider/temperature/limit change is allowed after this freeze without invalidating and re-freezing the comparison protocol.


## DEV01 reset after invalid run
Initial reset attempt encountered OUTPUT_FILE_IN_USE from the residual LibreOffice process bound to the invalid DEV01 profile. That attempt is NOT counted as PASS.
Residual process tree:
- soffice.exe PID 3040
- soffice.bin PID 12560
Both were tied to stage7/dev_runs/dev01/lo-profile and output.ods.
After terminating only that residual tree, the run directory was recreated and output.ods was copied from the original development fixture.
DEV01_RESET=PASS
RESET_HASH_MATCH=PASS
FORENSIC_INVALID_RUN_COPY_PRESERVED=true

Model freeze semantics:
- model_contract_frozen=true
- baseline_implementation_frozen=false
The provider/model/temperature/limits are frozen now; baseline implementation code remains under development until its own dry-run freeze gate.

## M1 free-quota budget and proof calendar
OpenRouter Free limit used by this protocol: 50 requests/day.

Maximum proof demand:
- 5 tasks x 3 repetitions x 2 systems x 8 model calls = 240 requests.
- Minimum proof duration at the 50/day ceiling = 5 calendar days.
- Each paired task/repetition can consume at most 16 calls.
- At most 3 complete pairs run on one proof day = 48 calls/day.
- The remaining 2 daily requests are safety margin.

Development / dry-run quota:
- Development days: maximum 40 model calls/day.
- 10 calls/day remain unused as quota/error margin.
- Proof days: development allocation = 0 calls.

Frozen proof calendar from RANDOMIZATION_SEED=20261001:
- Proof Day 1: T01/R1, T01/R2, T01/R3
- Proof Day 2: T02/R1, T02/R2, T02/R3
- Proof Day 3: T03/R1, T03/R2, T03/R3
- Proof Day 4: T04/R1, T04/R2, T04/R3
- Proof Day 5: T05/R1, T05/R2, T05/R3

Within each pair, BASELINE/ARBM order follows randomization/run_order.json exactly.

Quota exhaustion rule:
- BASELINE and ARBM of a pair must run on the same calendar day.
- If quota is exhausted after either member has started, the entire pair is BENCHMARK_INVALID with cause=PAIR_QUOTA_EXHAUSTED.
- Neither member enters performance metrics.
- The full pair is rerun from reset on the next available proof day before later scheduled pairs.
- Later pairs shift forward as needed, with a maximum of 3 complete pairs/day.


## API key hygiene and rotation policy
OpenRouter benchmark key:
- display_name=ARBM-SIST-M1-BENCHMARK
- created_date=2026-10-01
- validity_days=30
- expiration_date=2026-10-31
- key_credit_limit_usd=0
- full key value must never appear in repository files, logs, stdout, stderr, screenshots, prompts, responses, commits, or chat transcripts
- current plaintext repository scan: FULL_KEYLIKE_TOKEN_HITS=0
- KEY_POSSIBLY_EXPOSED=false based on available artifacts and observed outputs

Schedule fit:
- remaining development plus the 5 proof days must complete on or before 2026-10-31
- if the schedule can no longer fit before expiration, rotate the key before the next proof day

KEY_ROTATION rule:
- rotation is allowed only between proof days
- rotation is forbidden after either member of a benchmark pair has started and before that pair is complete
- replacement key must use the same OpenRouter account/workspace policy, MODEL_ID=qwen/qwen3.8-27b:free and key_credit_limit_usd=0
- rotation must be logged as KEY_ROTATION, never MODEL_DRIFT
- provider/model/temperature/agent limits remain unchanged across key rotation
- any pair interrupted by credential expiry or rotation is BENCHMARK_INVALID and must be rerun from reset


## Item 1 — OpenRouter credential state
Completed on 2026-10-01.
- active_key_label=ARBM-SIST-M1-BENCHMARK-V2
- expiration=2026-10-31T17:43:00-03:00
- user_environment_binding=PASS
- child_process_binding=PASS
- repository_plaintext_key_hits=0
- KEY_ROTATION=2026-10-01
- previous benchmark key superseded
- key rotation is not MODEL_DRIFT
- HTTP 402 or key quota/credit errors are KEY_CONFIG_ERROR and do not count as MODEL_VISION_PROBE attempts
