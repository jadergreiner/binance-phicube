# Conhecimentos Específicos — Risk Manager

## Position Sizing e Alocação

- Modelos de position sizing: risco fixo por operação (Fixed Fractional), Kelly Criterion, volatility-based sizing
- Regras de alocação máxima de capital por símbolo e por operação simultânea
- Impacto da alavancagem no risco real de liquidação
- Cálculo de margem requerida em Futures USDT-M

## Métricas de Performance e Risco

- Drawdown: absoluto, relativo e máximo (Maximum Drawdown)
- Sharpe Ratio, Sortino Ratio e Calmar Ratio
- Expectativa matemática: win rate × reward/risk
- Profit Factor e sua relação com consistência da estratégia

## Riscos Operacionais em Sistemas Automatizados

- Risco de execução: slippage, ordens não preenchidas, latência
- Risco de conectividade: bot offline, perda de SL/TP em caso de queda
- Risco de overfitting em parâmetros otimizados via backtesting
- Risco de regime: degradação de performance em mercados não contemplados no histórico de treino

## Controles de Risco

- Definição de circuit breakers: regras de pausa automática por drawdown diário, semanal ou mensal
- Limites de concentração: máximo de posições abertas simultâneas por símbolo
- Regras de capital máximo alocado em operações abertas
