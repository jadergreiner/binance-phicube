## Why

O circuit breaker atual (SPEC_043) reduz risco de forma reativa, mas ainda permite entradas em cenarios de baixa liquidez e alta volatilidade relativa, onde o slippage esperado pode ser desproporcional ao risco do setup. Precisamos de uma gate preditiva para bloquear ciclos perigosos antes da abertura de posicao.

## What Changes

- Adicionar uma gate preditiva no fluxo de decisao de risco para pular o ciclo quando a combinacao de liquidez baixa e ATR relativo extremo indicar risco elevado de slippage.
- Definir regra inicial baseada em percentil historico do ATR ratio (janela de 100 candles, gatilho no percentil 85), com parametrizacao em configuracao.
- Emitir log estruturado para cada bloqueio preditivo com metricas de decisao (tier, ATR ratio atual, percentil de referencia).
- Expor contagem de ciclos/trades pulados pelo circuito preditivo para consumo do dashboard/observabilidade.
- Estruturar a implementacao com padroes de projeto: `Strategy` para criterio de bloqueio, `Chain of Responsibility` no pipeline de gates e `Observer` para publicacao de eventos/metrica.

## Capabilities

### New Capabilities
- `predictive-circuit-breaker`: Bloqueio antecipado de entradas com base na combinacao de tier de liquidez e anomalia de volatilidade relativa (ATR/preco) antes da execucao do trade.

### Modified Capabilities
- None.

## Impact

- Codigo afetado: `src/trading/risk_manager.py`, possivelmente `src/config/settings.py`, camadas de metricas/telemetria e endpoints/servicos de dashboard que agregam counters de risco.
- Operacao: reduz exposicao a slippage extremo em pares de baixa liquidez, com potencial de diminuir frequencia de entradas em momentos adversos.
- Dependencias funcionais: reaproveita infraestrutura ja introduzida em SPEC_043 (tiers de liquidez e criterios de protecao de slippage).
