# Responsabilidades — QA Engineer

## Manutenção e Expansão da Suite de Testes

- Manter os testes unitários existentes (indicadores, signal engine) e garantir que continuem passando
- Ampliar a cobertura para os módulos: `risk_manager`, `order_manager`, `repository`, `main`
- Meta de cobertura mínima: 80% em todos os módulos críticos
- Garantir que `pytest` rode sem erros em CI antes de qualquer merge para `main`

## Testes de Integração

- Implementar testes de integração contra a Binance Testnet para validar:
  - Conexão e autenticação com `BinanceClient`
  - Criação de ordens de mercado, stop loss e take profit
  - Consulta de saldo e posições abertas
- Implementar testes de integração com MongoDB:
  - Persistência e recuperação de trades e sinais
  - Unicidade do índice em `entry_order_id`
  - Comportamento de `get_open_trades()` com múltiplos registros

## Testes de Cenários Críticos

- Cobrir os seguintes cenários de falha:
  - API da Binance retorna timeout: o bot recupera corretamente?
  - SL/TP falham após abertura da posição: `cancel_all_orders` é chamado?
  - Sinal detectado quando `max_open_positions` já atingido: posição é ignorada?
  - Símbolo já em operação aberta: novo sinal é ignorado?
  - MongoDB indisponível: o bot falha com elegância sem crashar?

## Testes de Regressão

- Executar suite completa de testes a cada mudança no `signal_engine.py` e `indicators.py`
- Validar que refatorações no backend não alteram o comportamento esperado dos sinais
- Manter fixtures de OHLCV representativos de diferentes regimes de mercado (tendência, lateral, volátil)

## Documentação de Qualidade

- Manter um registro dos cenários testados e dos limites conhecidos do sistema
- Reportar ao Backend Sênior e ao Product Owner os riscos identificados não cobertos por testes
