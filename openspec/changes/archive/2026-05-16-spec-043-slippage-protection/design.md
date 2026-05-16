## Context

A SPEC_043 define três proteções complementares: `priceProtect` em ordens de saída, validação de slippage no gate de risco e circuit breaker por perdas consecutivas. O objetivo é alinhar risco real ao risco configurado por trade.

Restrições: manter arquitetura async-first, não alterar estratégia BO Williams, preservar contrato atual do fluxo de execução e compatibilidade com testnet/simulação.

## Goals / Non-Goals

**Goals:**
- Aplicar `priceProtect` em SL/TP de forma padronizada.
- Bloquear entradas com `total_risk_usdt` acima do limite tolerado.
- Reduzir `risk_per_trade_usdt` automaticamente sob drawdown sequencial.
- Tornar `max_position_pct` um limitador adicional ao teto absoluto.

**Non-Goals:**
- Reescrever engine de sinais ou lógica de entrada da estratégia.
- Introduzir persistência cross-process para estado do breaker nesta SPEC.
- Implementar novas exchanges.

## Design Decisions

1. **Template Method no RiskManager para gate de risco real**
- Fluxo base: calcular risco teórico -> estimar slippage -> validar tolerância -> retornar sizing.
- Garante ordem determinística e ponto único de rejeição.

2. **Strategy para cálculo de slippage por liquidez**
- Estratégia atual orientada a tiers (`high/medium/low`) com fallback seguro.
- Prepara extensão futura para estratégia dinâmica por volatilidade sem quebrar chamadas.

3. **State para circuit breaker**
- Estado explícito evita regras espalhadas em condicionais ad hoc.
- Transições claras e auditáveis por log estruturado.

4. **Adapter no BinanceClient**
- Cliente concreto traduz contrato interno para payload CCXT/Binance, encapsulando `priceProtect` sem contaminar camadas superiores.

5. **Decorator para observabilidade**
- Rejeições e eventos de breaker recebem metadados adicionais sem alterar domínio principal do sizing.

## State Model (Circuit Breaker)

- `NORMAL`: risco base ativo.
- `REDUCED_RISK`: risco reduzido após `N` perdas consecutivas.
- `RECOVERY`: conta vitórias para retornar ao baseline.
- Retorno para `NORMAL` quando `recovery_wins_needed` for atingido.

## Risks / Trade-offs

- [Risco] threshold baixo pode reduzir risco cedo demais.
  - Mitigação: defaults conservadores e parâmetros validados em settings.
- [Risco] slippage estimada conservadora reduzir frequência de trades.
  - Mitigação: métricas de rejeição e ajuste de tiers por evidência.
- [Trade-off] mais regras no RiskManager aumenta complexidade local.
  - Mitigação: separar funções puras (_estimate_slippage, _apply_circuit_breaker).

## Migration Plan

1. Atualizar settings com novos parâmetros e validações.
2. Aplicar `priceProtect` em ordens de proteção no cliente Binance.
3. Implementar gate de slippage no `RiskManager.calculate()`.
4. Implementar estado e transições do circuit breaker.
5. Integrar registro de resultado de trade no ponto de fechamento.
6. Cobrir com testes unitários e validação OpenSpec strict.

## Open Questions

- O breaker deve operar apenas por instância de monitor (par) ou também em escopo global de portfólio nesta mesma change?
- O fallback de `priceProtect` em recursos não suportados deve registrar warning único por símbolo para reduzir ruído?