# Nova autorização de desembolso: teto de R$25,00

A autorização do usuário substitui a autorização anterior de recarga zero.
O novo desembolso máximo é **R$25,00**, com histórico contabilizado separadamente.
Não autoriza recarga automática, assinatura, recorrência nem conversão estimada
como prova do débito final. **Desembolso realizado: R$0,00.**

Foi aberta novamente a página oficial de faturamento do AI Studio. A estrutura
do painel apareceu, mas houve redirecionamento para a documentação de regiões
antes de mostrar conta, saldo ou checkout. Não foi possível determinar a causa
específica nem confirmar o projeto da chave PAID. A consulta de faturamento no
Google Cloud terminou em erro de autenticação HTTP 400, sem retry. A busca
restrita de recibos na conexão Gmail não encontrou correspondências e não
confirmou a conta proprietária. Nenhum dado de cartão, chave ou token foi
preservado neste pacote.

- **Valor mínimo exigido em BRL:** desconhecido; checkout não alcançado.
- **Valor que falta:** desconhecido; não há débito final em BRL para comparar.
- **Motivo:** acesso financeiro indisponível, anterior à decisão de compra.
- **Prova do checkout:** inexistente; nenhuma compra foi confirmada.

A [documentação oficial](https://ai.google.dev/gemini-api/docs/billing) publica
compra mínima de US$5 e informa que a interface apresenta o mínimo aplicável
à região e ao nível da conta. Isso não demonstra o débito final em reais desta
conta e não permite afirmar que R$25,00 sejam suficientes ou insuficientes.

O histórico permanece em US$3,774369 de uso registrado, sem equivaler a fatura
reconciliada. As lacunas dos runs 34511385723 e 34535970921 continuam abertas;
saldo real e limite comprovado por chamada também permanecem desconhecidos.
A autorização de pagamento não comprova crédito disponível nem admite execução.
Nenhum probe, chamada paga, smoke ou preparo de VM foi iniciado.

**Ação humana necessária:** abrir o
[AI Studio Billing](https://aistudio.google.com/billing) no navegador do Codex
com a conta proprietária do projeto de `GEMINI_G3_PAID_CERT_KEY` e deixar a página
autenticada acessível. Não é solicitada compra manual nesta etapa.

Estado: **BLOCKED_NOT_GREEN_PROVEN**, resultado **NO_RESULT/BLOCKED**.
Código, workflows, modelo, benchmark e FREE permanecem preservados; os gates
locais anteriores não foram reabertos. Auditoria C permanece bloqueada.
Registro estruturado: [brl25-authorization-ledger.json](brl25-authorization-ledger.json).
Os registros anteriores de autorização zero são históricos e foram substituídos
por esta autorização, sem que isso altere resultados de runs anteriores.
