# Conhecimentos Específicos — Quant Developer

## Indicadores Técnicos

- Implementação fiel dos indicadores de Bill Williams: Alligator (SMMA com offsets), Awesome Oscillator, Accelerator Oscillator, Fractais de 5 barras
- Diferença entre SMA, EMA, SMMA (Wilder's MA) e DEMA — impacto nos resultados da estratégia
- Identificação e tratamento de look-ahead bias na implementação de indicadores
- Cálculo correto de fractais: janela de 5 barras, exclusão das 2 últimas candles (incompletas)

## Backtesting

- Construção de backtesting vetorizado (sem loop candle a candle) para performance
- Tratamento correto de dados: exclusão da última candle aberta, alinhamento de timeframes
- Métricas de avaliação: win rate, profit factor, drawdown máximo, expectativa, Sharpe Ratio
- Identificação de overfitting: walk-forward analysis, out-of-sample testing
- Simulação realista de execução: slippage, spread, taxas da Binance Futures

## Dados e Séries Temporais

- Download e armazenamento de dados históricos OHLCV da Binance
- Resample de timeframes (ex: 1m → 15m) sem introduzir viés
- Tratamento de gaps, candles duplicadas e anomalias nos dados
- Normalização e alinhamento de múltiplos símbolos e timeframes

## Estatística Aplicada

- Testes de significância estatística para resultados de backtesting
- Distribuição de retornos: média, desvio padrão, skewness, kurtosis
- Correlação entre símbolos e impacto na diversificação do portfólio
