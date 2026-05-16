## Why

A estratégia atual protege risco teórico por trade, mas ainda permite perdas reais acima do teto configurado quando há slippage em pares de baixa liquidez e gatilhos de stop por `last price`. O resultado é erosão de capital mesmo com win rate alto.

## What Changes

- Adicionar `priceProtect: True` em ordens `STOP_MARKET` e `TAKE_PROFIT_MARKET` no cliente Binance.
- Expandir o `RiskManager` com estimativa de slippage por tier de liquidez e rejeição quando risco total exceder tolerância.
- Introduzir circuit breaker por perdas consecutivas com redução temporária de risco por trade e reset controlado.
- Migrar limite de posição máxima para modelo híbrido: absoluto + percentual do saldo.

## Capabilities

### New Capabilities
- `slippage-protection`: gate de risco real que combina risco teórico e slippage estimada antes da entrada.
- `loss-circuit-breaker`: controle de estado de drawdown por sequência de perdas.

### Modified Capabilities
- `exchange-order-protection`: ordens de proteção passam a usar `priceProtect` quando suportado.
- `risk-sizing`: passa a considerar `max_position_pct` junto do limite absoluto existente.

## Pattern-Oriented Architecture

- **Strategy**: seleção de cálculo de slippage por tier de liquidez.
- **Adapter**: `BinanceClient` adapta parâmetros da exchange ao contrato interno de proteção.
- **Template Method**: pipeline de validação no `RiskManager.calculate()` com etapa obrigatória de slippage.
- **Decorator**: enriquecimento não invasivo de logs/rejeições com metadados de slippage e breaker.
- **State**: circuito de perdas com transições `NORMAL -> REDUCED_RISK -> RECOVERY -> NORMAL`.

## Impact

- Affected code: `src/exchange/binance_client.py`, `src/trading/risk_manager.py`, `src/config/settings.py`, integração de fechamento de trade no monitor principal.
- API impact: sem breaking change externo; mudanças internas de proteção e configuração.
- Operational impact: menor incidência de perda acima do risco configurado em cenários de baixa liquidez.