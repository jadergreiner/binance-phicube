# SPEC_025 — Sinais no Dashboard + Diagnóstico de Não Execução

**ID:** SPEC_025  
**Status:** Concluída  
**Data:** 2026-05-08  
**Prioridade:** Alta

## 1. Objetivo

Adicionar visibilidade operacional dos sinais detectados no dashboard e persistir, por sinal, o desfecho de execução para explicar de forma rastreável por que houve ou não abertura de trade.

## 2. Regras de Negócio

- O dashboard deve exibir os **últimos 50 sinais** com ordenação por `detected_at` decrescente.
- Cada sinal novo detectado deve receber desfecho persistido:
  - `TRADE_OPENED` quando abre trade.
  - Um status `REJECTED_*` quando não abre trade por bloqueio operacional.
- Sinais antigos (pré-rastreio) permanecem sem backfill e devem aparecer como:
  - `execution_status = UNKNOWN_LEGACY`
  - `execution_reason = causa indisponível (pré-rastreio)`.

## 3. Contratos de API

### GET /signals/history

Resposta `200`:
- `{ signals: [...], total, generated_at }`
- limite fixo de 50 registros
- campos por sinal:
  - `symbol`, `timeframe`, `direction`, `entry_price`, `stop_loss`, `take_profit`,
  - `risk_reward_ratio`, `detected_at`,
  - `execution_status`, `execution_reason`, `execution_details`, `trade_id`, `outcome_at`.

Erros:
- `503` quando repositório indisponível.

## 4. Implementação

- Repository:
  - `save_signal` reutilizado para gravação inicial.
  - `update_signal_execution_outcome(...)` para persistir desfecho por `signal_id`.
  - `get_signal_history(limit=50)` para leitura da seção.
- TradingMonitor:
  - após `save_signal`, gravar desfecho em todos os caminhos pós-sinal:
    - saldo insuficiente,
    - rejeições de risco (`MAX_CAPITAL`, `ZERO_STOP`, `QTY_ZERO`, `MIN_NOTIONAL`),
    - falha de execução de ordem,
    - sucesso com `trade_id`.
- RiskManager:
  - expõe rejeição estruturada via `last_rejection/consume_last_rejection` sem alterar assinatura de `calculate`.
- Frontend:
  - nova seção “Sinais Gerados” com tabela e polling de 60s.
  - renderização de `UNKNOWN_LEGACY` para registros históricos.

## 5. Critérios de Aceite

- [x] `GET /signals/history` retorna 200 com payload e ordenação esperados.
- [x] `GET /signals/history` retorna 503 sem repositório/erro de DB.
- [x] Datas `detected_at/outcome_at` normalizadas em ISO UTC.
- [x] Desfechos de execução persistidos para novos sinais.
- [x] UI mostra seção de sinais e consome endpoint dedicado.
