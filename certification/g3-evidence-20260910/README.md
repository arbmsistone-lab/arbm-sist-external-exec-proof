# ARBM SIST G3 — Evidence Pack de bloqueio e correção

Estado: **BLOCKED_NOT_GREEN_PROVEN**. Este pacote não certifica o benchmark.

Atualização da consulta financeira: [acesso à conta bloqueado](FINANCIAL-BLOCKER.md).
Nenhum saldo ou valor faturado foi presumido; pagamento admissível nesta etapa: US$0,00.

## ACHADO

O [run 34535970921](https://github.com/arbmsistone-lab/arbm-sist-external-exec-proof/actions/runs/34535970921)
falhou na primeira chamada ao Gemini com `429 RESOURCE_EXHAUSTED` e a mensagem
`Your prepayment credits are depleted`. Houve oito tentativas, nenhuma ação
executada e nenhum `result.txt` oficial. A etapa de execução retornar sucesso no
workflow não comprova execução funcional: o harness registrou a exceção na trajetória.

- Repositório: `arbmsistone-lab/arbm-sist-external-exec-proof`.
- Branch: `g3/paid-cert-lane-20260910`.
- Candidate original: `06625444d3cdb45a93865daf91769f1c9ff44559`.
- Run SHA: `f26ba87020ceaefc01d22e0a592fbc864d0d9291`.
- OSWorld-V2: `v2026.08.08`, SHA `d578d2d4e0dc82b43e270fdaa7fa89d9708cd154`.
- Modelo: `gemini-3.5-flash`; limite de passos permanece 100.
- Artifact: `10175736158`, preservado em [failed-run-artifact.zip](failed-run-artifact.zip).
- SHA-256 do ZIP, verificado contra o digest do GitHub:
  `6f3b2dd557191cb182d5981ca727bd76b3f4af5fd6b035f2372a99d113d425cb`.

## RCA

1. Causa dominante: o provedor informou esgotamento dos créditos pré-pagos.
   Modificar o agente não recompõe saldo nem comprova a contabilidade da conta.
2. O retry genérico repetiu uma rejeição financeira terminal oito vezes, de
   22:14:56.756Z a 22:19:42.362Z, consumindo cerca de 285,6 segundos.
3. O limite de custo anterior era por task; o reset zerava a contabilidade.
   Não existia admissão conjunta de smoke/probe baseada no histórico do teto total.
4. O probe `34511385723` recebeu HTTP 200, mas a validação de texto falhou antes
   de imprimir ou preservar uso. Esse consumo é desconhecido.
5. O run anterior de 38 passos acumulou 587.272 tokens e US$0,9445305 registrados.
   O prompt cresceu de 2.521 para 30.757 tokens. A compactação candidata não chegou
   a ser exercitada no run atual por causa da rejeição na primeira chamada.
6. Trajetórias anteriores contêm terminal, scripts e instalação de pacotes.
   [historical-action-audit.json](historical-action-audit.json) identifica 17 passos
   com padrões de shell/instalação. São evidências de falha; não provas de execução limpa.

## CORREÇÃO

- Smoke e probe compartilham exclusão de concorrência e admissão financeira antes
  da preparação da VM ou chamada paga. A admissão exige reconciliação, crédito,
  reserva, histórico de runs, branch/repositório corretos, três auditorias e hashes.
- A configuração versionada bloqueia novas chamadas: custo histórico incompleto,
  crédito esgotado e limite por chamada ainda não comprovado. Reruns e reservas
  reutilizadas também são recusados.
- O adapter não repete chamadas de geração. O retry do SDK pinado foi desativado;
  falha terminal sobrevive ao reset e mensagens brutas do provedor não são registradas.
- O diário registra início, conclusão ou falha, tokens, custo, latência, task,
  passo, SHA e mudança de screenshot. Uso ausente continua desconhecido.
- O gasto do processo sobrevive ao reset da task. O contexto da task é limpo e
  a compactação preserva turnos de função completos e assinaturas originais.
- O agente bloqueia quatro observações consecutivas sem mudança de screenshot,
  comandos de shell/instalação reconhecidos e atalhos de terminal, antes de aceitar
  o turno. Esperas declaradas acima de dois segundos são recusadas. A saída do
  modelo foi limitada a 2.048 tokens.
- A verificação exige score oficial finito igual a 1.0 para PASS completo.
  A contabilidade e o upload ocorrem também em falhas; retenção de novos artifacts: 30 dias.

## PROVA

[local-tests.txt](local-tests.txt): 22 testes passaram, com chamadas de provedor
simuladas. [lint.txt](lint.txt): aprovado. Compilação dos cinco arquivos Python e
`git diff --check`: aprovados. Nenhuma VM, modelo local ou inferência paga foi executada.

[audit-3x.json](audit-3x.json) registra A=PASS_LOCAL, B=PASS_LOCAL, C=BLOCKED.
Os arquivos da lane FREE, snapshot de computer-use, agente vendor e parser vendor
permanecem idênticos ao baseline. A FREE também não mudou desde a separação PAID.
Isso comprova preservação do código; não substitui certificação funcional remota.
Task, evaluator, assets, VM e seus critérios não foram alterados nesta correção.

## CUSTO

| Evidência recuperada | Custo calculado |
| --- | ---: |
| Dez smokes com diário de uso | US$3,7688400 |
| Dois probes com tokens nos logs | US$0,0055290 |
| Total registrado | **US$3,7743690** |
| Teto autorizado | US$5,0000000 |
| Diferença aritmética, sem autorização de gasto enquanto houver lacunas | US$1,2256310 |

O probe `34511385723` e as rejeições do run `34535970921` não têm uso reconciliado.
O total registrado não é uma fatura completa nem prova de saldo disponível. Nenhum
novo run pago ou chamada ao modelo foi iniciado neste trabalho. Não houve compra
de infraestrutura ou crédito.

Preços usados: US$1,50/milhão de tokens de entrada e US$9,00/milhão de saída,
incluindo thinking, confirmados na [tabela oficial](https://ai.google.dev/gemini-api/docs/pricing).
O detalhamento e os SHAs estão em [run-ledger.json](run-ledger.json); os dez diários
originais foram preservados em `usage/`.

## PERFORMANCE

O bloqueio financeiro versionado impede preparar outra VM sem os requisitos.
O teste de crédito esgotado faz uma única tentativa simulada, sem sleep ou retry.
A compactação foi testada em 60 ciclos de interação, mantendo até sete mensagens.
Isso comprova limites locais; latência real, custo por task e ganho funcional do
candidato corrigido ainda não foram medidos no benchmark.

A detecção por hash mede mudança visual exata, não progresso semântico. A filtragem
de comandos não prova a segurança de toda interação GUI possível. Uma trajetória
aprovada ainda precisa de revisão. Reutilização de VM entre tasks/lotes e estabilidade
não foram exercitadas, pois não há admissão financeira para novo smoke.

## ESTADO

| Gate | Resultado |
| --- | --- |
| Evaluator oficial / execução funcional | Não comprovado |
| Estabilidade / certificação completa | Não comprovado |
| Preservação dos arquivos FREE e isolamento PAID | Aprovado localmente |
| Proteção de secrets nos novos registros | Testada com secret sintético; sem valores reais incluídos |
| Contabilidade total / crédito disponível | Bloqueado |
| Limite financeiro rigoroso por chamada | Não comprovado; reserva anterior ainda é heurística |
| SHA / runs / artifact atual / diários | Rastreáveis e preservados |
| GREEN_PROVEN global | **Não atingido** |

## PRÓXIMA AÇÃO

Reconciliar a cobrança ausente e o saldo no mesmo projeto Gemini, mantendo o teto
total de US$5. Não substituir a chave, mudar o modelo, comprar crédito ou lançar
smoke para investigar esse bloqueio. Antes de nova admissão, substituir a reserva
heurística por um limite comprovado de custo máximo da chamada e concluir auditoria C.
Somente então cabe um smoke válido, seguido de estabilidade e projeção de custo da
certificação completa. Não existe baseline PASS que permita projetar esse fechamento.

## Reprodução sem custo de modelo

Em um checkout desta branch, com Python 3.12, `google-genai==1.32.0`, PyYAML e Ruff:

```text
python -m unittest discover -s tests -p "test_g3_paid*.py" -v
python -m ruff check certification/g3_paid_control.py certification/g3_build_evidence.py certification/g3-gemini-fc-adapter.py tests/test_g3_paid_control.py tests/test_g3_paid_workflows.py
python certification/g3_paid_control.py --ledger certification/g3-paid-budget.json --output admission-check.json
```

O último comando deve terminar com código 1 e `G3_HISTORICAL_COST_UNRECONCILED`,
sem chamada de rede ou modelo. Os manifests preservam SHA-256 dos arquivos de
origem. Para reconstruir a contabilidade a partir dos downloads originais:

```text
python certification/g3_build_evidence.py --evidence-root ../g3-evidence --output certification/g3-evidence-20260910
```

A reconstrução redefine auditorias como pendentes por segurança. Não transforma
evidência ausente em zero nem reabre a lane PAID.
