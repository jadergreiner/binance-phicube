## Baseline Operacional (BO puro)

### Objetivo
Definir baseline canônico para comparar impacto da camada ML auxiliar em shadow mode.

### Escopo da Janela
- Periodo recomendado: 7 a 14 dias corridos.
- Timeframes: mesmos ativos monitorados em producao.
- Universo: todos os `symbol:timeframe` ativos no runtime.

### Fonte de Dados
- Trades fechados: `trades` (status fechados válidos)
- Sinais: `signals`
- Diagnóstico por ciclo: `audit.event = signal_cycle_diagnostic`
- Endpoints de apoio:
  - `/performance/assertiveness`
  - `/signals/history`
  - `/signals/diagnosis/{symbol}/{timeframe}`
  - `/symbols/{symbol}/detail`

### Métricas Baseline (BO puro)
1. Expectancy média por trade
2. Win rate
3. Profit factor
4. Max drawdown
5. Latência média/p95 de decisão de ciclo
6. Disponibilidade operacional (erros críticos por janela)

### Métricas Shadow (BO + apoio ML)
1. Cobertura ML (% ciclos com inferência válida)
2. Distribuição de score (`ml_score`)
3. Taxa por decisão (`ALLOW/BLOCK/ABSTAIN`)
4. Latência média/p95 de inferência ML
5. Taxa de erro de inferência ML

### Regras de Comparação
- Não alterar execução real nesta fase.
- Comparar impacto potencial por replay analítico (counterfactual):
  - sinais BO que ML teria bloqueado
  - sinais BO que ML teria permitido
- Consolidar resultados por símbolo e agregado.

### Critérios de Aceite (baseline pronto)
- Janela temporal definida com datas absolutas.
- Métricas baseline preenchidas e auditáveis.
- Cobertura shadow registrada para a mesma janela.
