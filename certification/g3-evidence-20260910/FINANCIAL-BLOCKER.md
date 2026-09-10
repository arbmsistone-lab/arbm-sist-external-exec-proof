# Reconciliação financeira — acesso externo bloqueado

O resultado funcional do run 34535970921 é **NO_RESULT/BLOCKED**. A causa
registrada continua sendo rejeição por créditos esgotados, não reprovação funcional
do evaluator. Nenhum novo probe, smoke, pedido de geração ou preparo de VM ocorreu.

O acesso direto a `https://aistudio.google.com/billing` exibiu inicialmente a
estrutura do painel e depois redirecionou para a documentação de regiões
disponíveis, antes de mostrar qualquer conta de faturamento ou valor. Não foi
possível verificar que a sessão corresponde ao projeto da chave PAID. Não há
conector de faturamento, configuração local Google Cloud ou identificador de
conta/projeto Gemini no material de configuração consultado. Os valores dos
secrets não foram lidos.

Uma tentativa de abrir o login visível na documentação foi rejeitada pela revisão
automática: o controle não era um alvo de faturamento verificado e o escopo de
autenticação não estava confirmado. A rejeição não foi contornada.

Os US$3,774369 dos diários continuam sendo consumo calculado a partir do uso
registrado, sem equivaler a fatura completa. Saldo real, total faturado e as duas
lacunas de cobrança permanecem desconhecidos. A margem segura e o limite comprovado
da próxima chamada também não foram demonstrados. Admissão atual: **US$0,00**.

A [documentação oficial de faturamento](https://ai.google.dev/gemini-api/docs/billing)
indica que saldo e transações de Prepay devem ser consultados no AI Studio Billing,
que há atrasos de processamento e que a compra mínima publicada é US$5. Isso não
comprova o saldo desta conta. Não há recarga positiva que possa ser recomendada
dentro desta autorização sem a reconciliação; a compra mínima publicada excede
a diferença aritmética ainda não reconciliada de US$1,225631.

**Única ação humana:** abrir o [AI Studio Billing](https://aistudio.google.com/billing)
com a conta Google proprietária do projeto da chave `GEMINI_G3_PAID_CERT_KEY`
e disponibilizar essa página autenticada para a consulta. **Pagamento: US$0,00.**
Não selecionar `Buy credits` nesta etapa. A ação resolve o acesso à evidência;
não pressupõe nem autoriza compra ou alteração da conta.

Os gates locais aprovados e o código do commit
`f7a3da12bfa72ce57c85b218a58f533f77450bf7` permanecem preservados. A auditoria C
continua bloqueada. O registro estruturado está em
[financial-access-blocker.json](financial-access-blocker.json).
