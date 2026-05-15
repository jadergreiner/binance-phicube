## Context

O bot ja possui protecoes de risco e slippage da SPEC_043, incluindo circuit breaker reativo e tiers de liquidez. O gap atual e que a entrada ainda pode ocorrer em condicoes pre-trade adversas (especialmente pares tier `low` com volatilidade relativa elevada), causando perdas por slippage antes de qualquer resposta reativa. A mudanca precisa respeitar o fluxo async existente, manter comportamento deterministico para testes e integrar com observabilidade do dashboard sem introduzir dependencia externa nova.

## Goals / Non-Goals

**Goals:**
- Adicionar gate preditiva no fluxo de risco antes da aprovacao final do trade.
- Usar criterio simples e auditavel: `ATR/close` atual contra percentil historico configuravel em janela fixa.
- Limitar bloqueio inicialmente a tiers de baixa liquidez para reduzir falsos positivos.
- Emitir telemetria estruturada e contador operacional para acompanhamento no dashboard.

**Non-Goals:**
- Nao introduzir modelo de ML, treinamento online ou inferencia estatistica avancada.
- Nao persistir estado historico entre reinicios alem do que ja e obtido por fetch de candles.
- Nao alterar estrategia de sinal (SignalEngine) nem regras de execucao de ordem (OrderManager).
- Nao substituir o circuit breaker reativo da SPEC_043; a logica nova e complementar.

## Decisions

1. **Local da gate: `RiskManager.calculate()` antes do position sizing**
   - **Racional:** centraliza todas as decisoes de aprovacao de risco em um unico ponto, reduzindo acoplamento com estrategia e execucao.
   - **Alternativas consideradas:**
     - `SignalEngine.evaluate()`: rejeitada por misturar risco operacional com logica de sinal.
     - `OrderManager.execute()`: rejeitada por estar tarde no fluxo (custos de processamento ja incorridos e menor clareza de observabilidade de skip).

2. **Criterio inicial: tier `low` AND `atr_ratio_atual > percentile(atr_ratio_hist, p)`**
   - **Racional:** usa variaveis ja disponiveis (tier de liquidez + ATR) e regra transparente para auditoria.
   - **Alternativas consideradas:**
     - Limiar absoluto fixo de ATR ratio: rejeitado por baixa adaptabilidade entre simbolos.
     - Critico para todos os tiers: rejeitado por risco de reduzir excessivamente throughput de trades.

3. **Parametros em configuracao (`predictive_breaker_percentile`, `predictive_breaker_window`, `predictive_breaker_tiers`)**
   - **Racional:** permite tuning sem alterar codigo e facilita rollout gradual.
   - **Alternativas consideradas:** hardcode no `RiskManager`, rejeitado por dificultar calibracao operacional.

4. **Observabilidade por evento estruturado e contador agregado**
   - **Racional:** torna o skip explicavel e mensuravel (ex.: `predictive_circuit_breaker_skipped`, `symbol`, `tier`, `atr_ratio`, `threshold`).
   - **Alternativas consideradas:** apenas log textual, rejeitado por baixa utilidade para dashboard e analise automatizada.

5. **Fallback defensivo em dados insuficientes/invalidos**
   - **Racional:** se historico insuficiente, `close<=0` ou ATR invalido, a gate nao deve bloquear por erro de dado; deve registrar motivo e seguir com demais validacoes.
   - **Alternativas consideradas:** bloquear por default, rejeitado por aumentar risco de indisponibilidade funcional.

6. **Pattern `Strategy` para regra preditiva**
   - **Racional:** encapsular a regra de decisao (`atr_ratio` vs percentil) em estrategia dedicada permite evoluir criterio sem inflar `RiskManager`.
   - **Alternativas consideradas:** regra inline no metodo `calculate()`, rejeitada por piorar testabilidade e clareza.

7. **Pattern `Chain of Responsibility` para gates de risco**
   - **Racional:** tratar gates (limite intraday, preditivo, stop distance) como cadeia ordenada reduz acoplamento e facilita inserir/remover gates.
   - **Alternativas consideradas:** blocos condicionais monoliticos, rejeitados por escalar mal com novas protecoes.

8. **Pattern `Observer` para telemetria de skip**
   - **Racional:** separa decisao de risco da entrega de observabilidade (logs/counters/dashboard), evitando dependencia direta de transporte.
   - **Alternativas consideradas:** chamadas diretas ao dashboard dentro do risco, rejeitadas por violar separacao de responsabilidades.

9. **Pattern `Adapter` para exposicao no dashboard**
   - **Racional:** um adaptador de metricas traduz o contador interno de skips para o contrato atual da API/dashboard sem quebrar consumidores.
   - **Alternativas consideradas:** alterar contrato diretamente no produtor de risco, rejeitada por aumentar impacto de compatibilidade.

## Risks / Trade-offs

- **[Risco]** Excesso de skips em mercado volatil de baixa liquidez reduz oportunidade de entrada.  
  **Mitigacao:** parametros configuraveis, monitoramento de taxa de skip e ajuste progressivo de percentil/janela.

- **[Risco]** Historico curto ou inconsistente distorce percentil.  
  **Mitigacao:** exigir tamanho minimo de janela valida; em ausencia, desativar gate para o ciclo com log de diagnostico.

- **[Risco]** Divergencia entre contrato de metricas e dashboard.  
  **Mitigacao:** definir nome canonico de contador e cobrir com testes de API/integracao.

- **[Risco]** Sobreposicao semantica com circuit breaker reativo gera interpretacao errada.  
  **Mitigacao:** nomenclatura explicita em logs/documentacao (`predictive` vs `reactive`) e testes separados.

## Migration Plan

1. Introduzir parametros de configuracao com defaults conservadores (feature inicialmente ativa apenas para tier `low`).
2. Implementar gate no `RiskManager` com logs estruturados e contador.
3. Adicionar testes unitarios (cenarios low/high/unknown tier, acima/abaixo do percentil, fallback de dados invalidos).
4. Atualizar endpoint/servico de metricas do dashboard para expor contador de skips preditivos.
5. Executar rollout controlado e acompanhar metricas operacionais por janela de observacao.
6. Rollback: desabilitar gate via configuracao (tiers vazios ou percentual inoperante) sem remover codigo.

## Open Questions

- O contador de skips preditivos sera exposto no endpoint existente de metricas de risco ou em campo dedicado no `/positions/health`/dashboard?
- Qual tamanho minimo de amostras valida historico para habilitar percentil (ex.: 50 de 100 candles)?
- A regra inicial deve usar comparacao estrita (`>`) ou inclusiva (`>=`) no limiar percentil?
- O rollout inicial em producao sera imediato ou protegido por feature flag desligada por padrao?
