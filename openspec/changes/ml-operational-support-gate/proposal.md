## Why

A estratégia BO Williams do Phicube é robusta como motor principal, mas ainda sofre com ruído de regime lateral e variabilidade de qualidade entre símbolos/timeframes. Precisamos de uma camada de apoio operacional que aumente assertividade e reduza exposição desnecessária sem substituir a lógica atual.

## What Changes

- Introduzir uma camada de predição **auxiliar** (não substitutiva) ao pipeline atual.
- Escopo funcional inicial:
  - Signal Quality Gate: score de probabilidade para aprovar/reprovar sinal BO.
  - Shadow Mode: cálculo e registro do score sem impacto em execução real.
  - Feature Flags por símbolo/timeframe para ativação controlada.
  - Métricas de impacto comparadas ao baseline BO puro.
  - Critérios objetivos de Go/No-Go para promoção.
- Restrição explícita desta etapa:
  - Não alterar execução real de ordens.
  - Não alterar contrato atual de entrada/saída do OrderManager.

## Non-Goals

- Substituir o SignalEngine BO Williams.
- Treino online autônomo em produção nesta fase.
- Mudar sizing final de risco sem passar pelos critérios de Go.

## Safe Rollout

1. Shadow mode por 2-4 semanas em produção.
2. Coleta de decisões paralelas (BO vs ML gate) por símbolo/timeframe.
3. Canary de ativação progressiva via feature flags somente após Go.
4. Rollback imediato: desabilitar flags e retornar para BO puro.

## Impact Metrics

- Delta de expectancy por trade vs baseline.
- Win rate e profit factor vs baseline.
- Redução de max drawdown.
- Taxa de bloqueio útil (sinais evitados que seriam perdedores).
- Latência adicional de decisão e disponibilidade da camada ML.

## Go/No-Go Criteria

Go apenas se, na janela de validação:

- Expectancy melhorar >= 10%.
- Max drawdown reduzir >= 15%.
- Sem degradação relevante de latência/SLA.
- Ganho consistente em múltiplos símbolos/timeframes (não concentrado em 1 outlier).

No-Go se houver:

- Ganho restrito a backtest sem evidência em shadow runtime.
- Instabilidade por regime (drift) sem mitigação.
- Complexidade operacional maior que o benefício líquido.

## Risks

- Overfitting por símbolo/timeframe.
- Drift de regime intraday.
- Falsa confiança em score alto sem contexto.
- Aumento de custo operacional de observabilidade e governança.

## Dependencies

- Persistência de diagnóstico já existente (audit/signals/history).
- Endpoints de diagnóstico e assertividade para comparação BO vs ML.
- Feature flags e configuração por símbolo/timeframe no runtime.
