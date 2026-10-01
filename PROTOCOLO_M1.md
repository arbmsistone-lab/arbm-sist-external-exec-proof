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
