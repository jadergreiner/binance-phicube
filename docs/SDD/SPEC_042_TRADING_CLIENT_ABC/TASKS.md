# TASKS — SPEC_042_TRADING_CLIENT_ABC

## 1. Contrato Base (ABC)

- [x] 1.1 Criar `src/exchange/base_client.py` com `TradingClient(ABC)` e métodos abstratos obrigatórios por domínio (lifecycle, market data, balance, leverage, orders, positions, precision).
- [x] 1.2 Implementar defaults no `TradingClient` para `validate_market_liquidity` e `fetch_quantity_precision_map` (Template Method parcial).
- [x] 1.3 Documentar docstrings do contrato em pt-BR com precondições e retorno esperado.

## 2. Implementações Concretas (Adapter/Strategy)

- [x] 2.1 Refatorar `src/exchange/binance_client.py` para herdar de `TradingClient` sem alterar comportamento funcional.
- [x] 2.2 Refatorar `src/exchange/simulated_client.py` para herdar de `TradingClient` preservando semântica de simulação.
- [x] 2.3 Garantir alinhamento de assinaturas e retornos entre clientes concretos e contrato base.

## 3. Consumidores Críticos (Facade de Dependência)

- [x] 3.1 Substituir `Any` por `TradingClient` em `src/trading/order_manager.py`.
- [x] 3.2 Substituir `Any` por `TradingClient` em `RuntimeMonitorRegistry` (`src/main.py`).
- [x] 3.3 Substituir `Any` por `TradingClient` em `src/monitoring/order_monitor.py` (se houver tipagem de client nesse módulo).

## 4. Validação e Evidências

- [x] 4.1 Executar lint/formatação dos arquivos Python alterados.
- [x] 4.2 Executar testes unitários relevantes de exchange/monitor/trading.
- [x] 4.3 Executar validação OpenSpec strict da change e corrigir inconsistências.
