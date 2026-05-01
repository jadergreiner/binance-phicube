# Responsabilidades — Quant Developer

## Implementação dos Indicadores

- Implementar e manter os indicadores técnicos da estratégia Phicube (`src/strategy/indicators.py`):
  - Alligator (Jaw, Teeth, Lips via SMMA com offsets corretos)
  - Awesome Oscillator (AO)
  - Fractais de Bill Williams (bearish e bullish, janela de 5 barras)
- Garantir que nenhum indicador introduza look-ahead bias
- Documentar as fórmulas e validar contra cálculos manuais no TradingView

## Motor de Sinais

- Implementar as regras de entrada Long e Short (`src/strategy/signal_engine.py`) em total alinhamento com o Trader Sênior
- Definir e implementar os filtros de qualidade de sinal (ex: rejeitar sinais em mercado lateral)
- Garantir que cada sinal produzido inclua entrada, stop loss e take profit calculados pelas regras do método

## Backtesting

- Construir e manter o módulo de backtesting da estratégia
- Produzir relatórios de performance para o Risk Manager e o Trader Sênior validarem
- Executar backtesting em novos símbolos e timeframes antes de adicioná-los em produção
- Identificar e reportar regressões de performance ao Trader Sênior

## Qualidade de Dados

- Manter scripts de download e atualização de dados históricos da Binance
- Garantir integridade dos dados: sem gaps, sem duplicatas, sem anomalias
- Suportar o ML/AI Engineer com dados limpos e bem estruturados para treino de modelos
