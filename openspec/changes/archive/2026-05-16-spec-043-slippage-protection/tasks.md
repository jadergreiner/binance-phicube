## 1. Adapter de Exchange (priceProtect)

- [x] 1.1 Atualizar `src/exchange/binance_client.py` para incluir `priceProtect: True` em `create_stop_loss_order`.
- [x] 1.2 Atualizar `src/exchange/binance_client.py` para incluir `priceProtect: True` em `create_take_profit_order`.
- [x] 1.3 Cobrir fallback seguro para casos não suportados sem quebrar execução.

## 2. Template Method + Strategy no RiskManager

- [x] 2.1 Implementar/ajustar etapa de estimativa de slippage por tier dentro do pipeline de `calculate()`.
- [x] 2.2 Validar `total_risk_usdt <= risk_per_trade_usdt * slippage_tolerance_multiplier`.
- [x] 2.3 Registrar rejeição com `SLIPPAGE_EXCEEDS_TOLERANCE` e metadados de observabilidade.

## 3. State Pattern no Circuit Breaker

- [x] 3.1 Implementar estado de perdas consecutivas e ativação de risco reduzido.
- [x] 3.2 Implementar recuperação por vitórias consecutivas com reset para baseline.
- [x] 3.3 Expor estado efetivo (`circuit_breaker_active`, `effective_risk_per_trade_usdt`) para consumo operacional.

## 4. Clamp de Exposição

- [x] 4.1 Adicionar configuração `max_position_pct` em settings e validações.
- [x] 4.2 Aplicar clamp híbrido (`min` entre teto absoluto e percentual do saldo).

## 5. Validação

- [x] 5.1 Adicionar/ajustar testes unitários de priceProtect, slippage gate e circuit breaker.
- [x] 5.2 Executar `ruff check` e `ruff format` nos arquivos alterados.
- [x] 5.3 Executar `openspec validate --strict spec-043-slippage-protection`.