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
