# SPEC_027 — Telemetria de No-Signal no Dashboard

**ID:** SPEC_027  
**Status:** Concluída  
**Data:** 2026-05-08  
**Prioridade:** Alta

## 1. Objetivo

Adicionar visibilidade operacional em tempo real para explicar por que não há novos sinais gerados por símbolo/timeframe.

## 2. Regras de Negócio

- Cada ciclo de avaliação do `SignalEngine` deve produzir telemetria estruturada (`signal_evaluated`), mesmo quando não há entrada.
- O dashboard deve exibir o diagnóstico mais recente por símbolo/timeframe no snapshot de posições.
- O comportamento de geração de sinal e persistência de sinais/trades não deve ser alterado.

## 3. Contrato

- Snapshot `GET /positions` e `WS /ws/positions` passa a incluir:
  - `signal_telemetry: list`
  - Campos por item: `symbol`, `timeframe`, `decision`, `signal_generated`, `reason`,
    `evaluated_at`, `evaluated_at_br`, `candle_open_time`, `candle_open_time_br`,
    `long_conditions`, `short_conditions`.

## 4. Implementação

- `SignalEngine` passa a armazenar última avaliação (`consume_last_evaluation`) com decisão e condições.
- `TradingMonitor` persiste telemetria em `audit` com evento `signal_evaluated` a cada `_tick`.
- `MongoRepository` expõe `get_latest_signal_diagnostics(...)` agregando por símbolo/timeframe.
- `positions` snapshot inclui `signal_telemetry`.
- Frontend adiciona seção “Diagnóstico de Sinais” renderizada a partir de `snapshot.signal_telemetry`.

## 5. Critérios de Aceite

- [x] Quando não há sinal, diagnóstico explicita decisão/motivo.
- [x] Dashboard mostra diagnóstico recente sem depender de logs.
- [x] Testes cobrem engine, monitor, repository, API e frontend.
