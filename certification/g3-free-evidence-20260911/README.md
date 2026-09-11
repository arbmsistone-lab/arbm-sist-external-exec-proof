# ARBM SIST G3 FREE — evidências de correção e reteste

Baseline: run 34545605068, SHA 47aee38f0873cdd3964aea5ef03caf6c982483be.
Branch: g3-free-cert-lane-20260910. Lane PAID congelada e preservada.

O baseline registrou 31 ações e reward 0.00. Nenhum artifact foi armazenado:
a resposta inválida e os screenshots não podem ser reconstruídos a partir dos logs.
O relatório baseline-rca.json distingue dados recuperados de dados perdidos.

A correção introduz um único contrato desktop_action, validação antes de emitir
PyAutoGUI, até dois retries estruturais sem execução, memória de estado limitada,
anti-loop, timeout total de 45s e limite de 1024 tokens de saída. O journal fecha
cada request inclusive falhas e registra interrupções sem inventar custo observado.
Cada modelo é fixo no experimento; não existe fallback para outro modelo.

Os 25 testes locais, compilação, lint e revisão 3x habilitam somente o reteste.
O workflow exige probe de imagem/tool/contexto e custo observado zero antes da VM.
O nome físico do resultado é sanitizado; a identidade original fica no journal e
model-identity.json. A trajetória oficial inteira é arquivada em tar.gz.

ZERO_SPEND: contrato obrigatório; chamadas reais novas ainda não executadas neste registro.
HEAVY_LOCAL=0. Resultados funcionais, estabilidade, suite e TOP3 continuam abertos.
