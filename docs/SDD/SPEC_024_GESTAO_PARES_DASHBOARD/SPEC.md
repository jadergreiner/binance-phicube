# SPEC_024 — Gestão de Pares no Dashboard (Sessão Inferior)

**ID:** SPEC_024  
**Status:** Concluída  
**Data:** 2026-05-08  
**Prioridade:** Alta

## 1. Objetivo

Evoluir o onboarding para gestão pós-aprovação de pares diretamente no dashboard, permitindo edição operacional de símbolo/timeframe/leverage, solicitação de backtest e análise técnica atual por símbolo.

## 2. Regras de Negócio

- Sessão `APPROVED` editada via `PATCH /onboarding/{symbol}` mantém status `APPROVED`.
- Quando sessão aprovada é alterada, `config_string` é recalculada e `SYMBOL_TIMEFRAMES` no `.env` é atualizado automaticamente.
- Rename de símbolo é permitido com validações:
  - não pode conflitar com símbolo ativo em runtime;
  - não pode conflitar com outra sessão existente.
- `POST /onboarding/{symbol}/backtest` aceita sessão `APPROVED`; em sucesso mantém `APPROVED`.
- `POST /onboarding/{symbol}/market-analysis` executa análise técnica síncrona do símbolo/timeframe atual da sessão.

## 3. Contratos de API

### PATCH /onboarding/{symbol}

**Body:** `{ symbol?, timeframe?, leverage?, notes? }`

Validações:
- `symbol`: regex `^[A-Z]{2,15}USDT$`
- `timeframe`: conjunto válido do onboarding
- `leverage`: inteiro entre 1 e 20

Respostas:
- `200` sessão atualizada
- `404` sessão não encontrada
- `409` conflito de símbolo ativo ou sessão existente
- `422` payload/campos inválidos

### POST /onboarding/{symbol}/market-analysis

Executa leitura de candles atuais, calcula contexto técnico (Alligator, AO, fractais recentes) e avalia sinal com `SignalEngine`.

Respostas:
- `200` payload com `signal_detected`, `signal` (opcional) e `context`
- `404` sessão não encontrada
- `503` indisponibilidade de mercado/binance/dados insuficientes

## 4. Frontend

- Ação `Ver Config` é substituída por `Gerenciar` para sessões `APPROVED`.
- Painel de gestão inclui:
  - edição de `symbol`, `timeframe`, `leverage`;
  - botão `Backtest`;
  - botão `Análise Atual`.
- Caixa de configuração passa a comunicar que o `.env` já foi atualizado automaticamente e mantém a linha aplicada para auditoria/cópia.

## 5. Critérios de Aceite

- [x] `PATCH` preserva `APPROVED` e reaplica `SYMBOL_TIMEFRAMES` no `.env`.
- [x] `PATCH` retorna `409` para rename inválido (símbolo ativo ou sessão existente).
- [x] `PATCH` retorna `422` para payload inválido.
- [x] Backtest em `APPROVED` retorna `200` e mantém estado.
- [x] `market-analysis` retorna payload técnico em sucesso e `503` em falhas de mercado.
- [x] Frontend exibe `Gerenciar`, executa `PATCH`, `backtest` e `market-analysis`.
