## Context

Foi identificado padrão de fechamentos `CLOSED_MANUAL` muito curtos com
`is_estimated=True` (ex.: 28-66s em ATOMUSDT), associado ao fluxo de
reconciliação do `OrderMonitor`. A investigação mostrou risco de comparação de
símbolos em formatos diferentes e decisões de fechamento manual com baixa
robustez após `OrderNotFound`/erros transitórios.

## Goals / Non-Goals

**Goals:**

- Garantir equivalência semântica de símbolo ao validar posição aberta.
- Evitar fechamento manual em falso positivo exigindo dupla confirmação temporal.
- Endurecer fallback quando ordem não é encontrada, com checagens adicionais de posição antes de encerrar trade.

**Non-Goals:**

- Alterar regras de entrada da estratégia de sinal.
- Redesenhar monitor de SL órfão nesta mudança.
- Mudar cálculo de PnL além do necessário para evitar fechamento indevido.

## Decisions

- Decisão 1: Introduzir normalização canônica de símbolo para comparações internas (`ATOMUSDT` <-> `ATOM/USDT:USDT`).
  - Racional: remove classe de falso negativo de posição aberta.

- Decisão 2: Exigir 2 ciclos consecutivos de "posição ausente" antes de `_handle_manual_close`.
  - Racional: filtra ruído de consulta e instabilidade temporária da exchange.

- Decisão 3: Em `OrderNotFound`, executar fallback robusto baseado em múltiplas evidências (estado de posição + estado de ordens remanescentes) antes de fechamento.
  - Racional: `OrderNotFound` isolado não prova encerramento real da posição.

## Risks / Trade-offs

- [Risco] Atraso adicional para reconhecer fechamento manual real.
  -> Mitigação: janela curta (2 ciclos) e logs explícitos de pendência de confirmação.

- [Risco] Complexidade maior no monitor.
  -> Mitigação: encapsular estado transitório com estrutura simples e testes unitários focados.

- [Trade-off] Menos sensível a fechamento instantâneo em troca de maior precisão.
  -> Mitigação: parametrizar número de confirmações para ajuste futuro.

## Migration Plan

1. Implementar normalizador de símbolo para comparações de posição.
2. Adicionar estado temporário de confirmação de ausência por `entry_order_id`.
3. Endurecer fluxo `OrderNotFound` com confirmação adicional antes de manual close.
4. Cobrir com testes de regressão para cenários de falso positivo.
5. Validar telemetria e impacto em histórico de trades.

## Open Questions

- A confirmação de 2 ciclos deve ser fixa ou configurável por ambiente?
- Quais campos mínimos de log serão obrigatórios para auditoria de "manual close confirmado"?
