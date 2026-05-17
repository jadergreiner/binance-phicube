## Relatório Go/No-Go — ML Operational Support

### 1) Janela de Avaliação
- Início: 2026-05-10T00:00:00Z
- Fim: 2026-05-17T23:59:59Z
- Ambiente: Docker local (`phicube` + `dashboard-api`)
- Universo de símbolos/timeframes: conjunto ativo no runtime e dados retornados por `/performance/assertiveness`

### 2) Baseline BO Puro
- Expectancy: não exposto diretamente; proxy observado com `total_pnl_usdt=-1406.3207` para `total_trades=36`
- Win Rate: 52.78%
- Profit Factor: 0.0041
- Max Drawdown: -1408.8787 USDT
- Latência média/p95 de ciclo: indisponível nesta coleta (endpoint de métricas do bot inacessível em `:8000`)
- Disponibilidade (incidentes críticos): sem evidência de indisponibilidade no `dashboard-api` durante a coleta

### 3) Shadow ML (Sem impacto real)
- Cobertura de inferência (% ciclos): 0.0% (`ml_cycles=0` de `total_cycles=518`)
- Distribuição de score (p50/p90): indisponível (sem inferências)
- Decisões ML (`ALLOW/BLOCK/ABSTAIN`): indisponível (sem inferências)
- Latência ML média/p95: indisponível (sem inferências)
- Taxa de erro de inferência: 0 (sem inferências)

### 4) Comparativo BO vs BO+ML (Counterfactual)
- Delta Expectancy (%): não calculável (sem amostra ML)
- Delta Drawdown (%): não calculável (sem amostra ML)
- Delta Win Rate (%): não calculável (sem amostra ML)
- Comentários por símbolo (top ganhos / top perdas):
  - Assertividade no período mostrou outlier negativo concentrado em `BTCUSDT` no ranking agregado.
  - Sem camada ML ativa, não há comparação válida BO vs ML.

### 5) Critérios Objetivos
- [ ] Expectancy >= +10%
- [ ] Drawdown <= -15%
- [ ] Sem degradação relevante de latência/SLA
- [ ] Ganho consistente em múltiplos símbolos/timeframes

### 6) Decisão
- Resultado: NO-GO
- Justificativa objetiva: camada ML não gerou inferências na janela (`ml_cycles=0`), portanto não há evidência estatística para comparar impacto e promover fase com influência operacional.
- Riscos remanescentes: sem cobertura shadow ativa, o projeto pode avançar sem validação quantitativa real.
- Plano de próxima fase: ativar `ml_support_enabled=true` mantendo `ml_support_shadow_mode=true` por janela mínima de 7-14 dias e repetir relatório.

### 7) Rollback / Segurança
- Flag para retorno imediato BO puro: `ml_support_enabled=false`
- Evidência de fallback testado: validado por testes focados (falha ML não interrompe ciclo e não altera decisão BO)
- Responsável pela aprovação: pendente

---

## Evidências coletadas

1. `/performance/assertiveness?period=custom&start=2026-05-10&end=2026-05-17`
- `summary.total_signals=12`
- `summary.total_trades=5`
- `summary.pnl_usdt=-1408.123`

2. `/performance`
- `total_trades=36`
- `win_rate_pct=52.78`
- `total_pnl_usdt=-1406.3207`
- `profit_factor=0.0041`
- `max_drawdown_usdt=-1408.8787`

3. Mongo audit (`signal_cycle_diagnostic`) na janela
- `total_cycles=518`
- `ml_cycles=0`
- `coverage_pct=0`
- `ml_errors=0`
