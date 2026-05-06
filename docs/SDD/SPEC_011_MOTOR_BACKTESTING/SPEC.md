# SPEC_011 — Motor de Backtesting

**ID:** SPEC_011
**Título:** Motor de Backtesting
**Data:** 2026-05-05
**Status:** Concluída
**Versão:** 1.0
**Dependências:** SPEC_006 (métricas), SPEC_009 (por símbolo/timeframe)
**PRD §:** Fase 2 — "Backtests e walk-forward analysis"

---

## 1. Objetivo

Implementar um motor de backtesting que reutiliza `SignalEngine`, `indicators.py` e `RiskManager`
para simular a estratégia BO Williams Phicube sobre dados históricos OHLCV, calculando as mesmas
6 métricas de performance já consolidadas (win rate, PnL, RRR médio, drawdown, profit factor).

O operador pode validar a estratégia contra dados históricos antes de operar em produção, sem
precisar de dados externos ou ferramentas terceiras.

---

## 2. Escopo

### Dentro do escopo
- Motor de backtesting barra-a-barra (sem look-ahead bias)
- CLI: `python -m src.backtest.runner --symbol BTCUSDT --timeframe 4h --limit 1000`
- Endpoint read-only: `GET /backtest?symbol=BTCUSDT&timeframe=4h&limit=500`
- Paginação de OHLCV (múltiplas chamadas de 200 candles)
- Métricas: total_trades, win_rate_pct, total_pnl_usdt, avg_rrr, max_drawdown_usdt, profit_factor

### Fora do escopo (SPEC futura)
- Walk-forward analysis (divisão em janelas temporais)
- Ajuste automático de parâmetros
- Equity curve gráfica
- Dados OHLCV externos (só Binance via `fetch_ohlcv`)

---

## 3. User Stories

### US-011-01 — Backtest via CLI
**Como** operador,
**quero** executar `python -m src.backtest.runner --symbol BTCUSDT --timeframe 4h --limit 1000`,
**para** ver as métricas de performance da estratégia sobre os últimos 1000 candles.

**Critério de aceite:**
- Imprime tabela de métricas no console
- Grava arquivo `backtest_results/BTCUSDT_4h_<timestamp>.json`

### US-011-02 — Backtest via API
**Como** operador,
**quero** chamar `GET /backtest?symbol=BTCUSDT&timeframe=4h&limit=200`,
**para** obter o resultado de backtest em JSON sem sair do painel.

**Critério de aceite:**
- 200 com `BacktestResult` serializado
- 422 para parâmetros inválidos
- 503 quando Binance indisponível

---

## 4. Modelo de Dados

### BacktestTrade

| Campo | Tipo | Descrição |
|---|---|---|
| `symbol` | `str` | Par negociado |
| `timeframe` | `str` | Timeframe usado |
| `direction` | `str` | `"LONG"` ou `"SHORT"` |
| `entry_price` | `float` | Preço de entrada (close do candle de sinal) |
| `sl_price` | `float` | Stop loss calculado pelo RiskManager |
| `tp_price` | `float` | Take profit calculado pelo RiskManager |
| `entry_candle_idx` | `int` | Índice do candle de entrada |
| `exit_candle_idx` | `int` | Índice do candle de saída |
| `exit_price` | `float` | Preço de saída (SL ou TP atingido) |
| `close_reason` | `str` | `"SL"` ou `"TP"` |
| `pnl_usdt` | `float` | P&L realizado (positivo=ganho, negativo=perda) |
| `rrr_realizado` | `float` | RRR efetivo do trade |

### BacktestResult

| Campo | Tipo | Descrição |
|---|---|---|
| `symbol` | `str` | Par negociado |
| `timeframe` | `str` | Timeframe usado |
| `candles_used` | `int` | Candles analisados (após warmup) |
| `trades` | `list[BacktestTrade]` | Todos os trades simulados |
| `total_trades` | `int` | Número de trades |
| `win_rate_pct` | `float` | Taxa de acerto (%) |
| `total_pnl_usdt` | `float` | PnL acumulado |
| `avg_rrr` | `float` | RRR médio realizado |
| `max_drawdown_usdt` | `float` | Maior queda pico→vale (negativo) |
| `profit_factor` | `float` | Soma ganhos / soma perdas absolutas |
| `generated_at` | `datetime` | Timestamp de geração |

---

## 5. Componentes

### 5.1 BacktestEngine (`src/backtest/engine.py`)

```python
class BacktestEngine:
    def __init__(self, settings: Settings, client: BinanceClient) -> None: ...
    async def run(self, symbol: str, timeframe: str, limit: int = 1000,
                  initial_balance: float = 1000.0) -> BacktestResult: ...
```

**Algoritmo:**
1. Buscar OHLCV paginado (lotes de 200 até atingir `limit`)
2. Descartar os `warmup_candles` primeiros candles
3. Loop barra-a-barra `i` de `warmup_candles` até `len(df)`:
   - Se sem trade aberto: `SignalEngine.evaluate(df.iloc[:i+1])` → sinal → abrir trade
   - Se trade aberto: verificar `high[i] >= tp` (TP hit) ou `low[i] <= sl` (SL hit)
   - Registrar `BacktestTrade` ao fechar
4. Calcular métricas agregadas → `BacktestResult`

### 5.2 Runner CLI (`src/backtest/runner.py`)

Entry point: `python -m src.backtest.runner`

Argumentos:
- `--symbol` (obrigatório)
- `--timeframe` (obrigatório)
- `--limit` (default: 1000)
- `--balance` (default: 1000.0)

### 5.3 Endpoint API (`src/api/routes/backtest.py`)

```
GET /backtest?symbol=BTCUSDT&timeframe=4h&limit=500&balance=1000
```

Respostas:
- `200` — BacktestResult como JSON
- `422` — parâmetros inválidos (FastAPI automático)
- `503` — Binance indisponível

---

## 6. Invariantes

| ID | Invariante |
|----|-----------|
| INV-011-01 | Sem look-ahead bias — candle `i` avalia apenas `df.iloc[:i+1]` |
| INV-011-02 | `warmup_candles` primeiros candles nunca geram trades |
| INV-011-03 | Um trade aberto por vez por (symbol, timeframe) na simulação |
| INV-011-04 | Falha no BacktestEngine não afeta o loop de trading ao vivo |
| INV-011-05 | `GET /backtest` é read-only — nenhuma ordem real é criada |

---

## 7. Testes

| ID | Descrição |
|----|-----------|
| TEST_011_01 | Sem trades → result com métricas zeradas/lista vazia |
| TEST_011_02 | 1 trade TP → win_rate=100%, pnl > 0 |
| TEST_011_03 | 1 trade SL → win_rate=0%, pnl < 0 |
| TEST_011_04 | Warmup respeitado — candles antes de warmup não geram trades |
| TEST_011_05 | max_drawdown calculado corretamente |
| TEST_011_06 | Runner CLI produz saída JSON válida (mock BinanceClient) |

---

## 8. Arquivos

| Arquivo | Mudança |
|---------|---------|
| `src/backtest/__init__.py` | Criado (vazio) |
| `src/backtest/models.py` | Criado — BacktestTrade, BacktestResult |
| `src/backtest/engine.py` | Criado — BacktestEngine |
| `src/backtest/runner.py` | Criado — CLI entry point |
| `src/api/routes/backtest.py` | Criado — GET /backtest |
| `src/api/main.py` | Modificado — incluir backtest_router |
| `tests/backtest/__init__.py` | Criado (vazio) |
| `tests/backtest/test_engine.py` | Criado — TEST_011_01 a 05 |
| `tests/backtest/test_runner.py` | Criado — TEST_011_06 |
| `docs/SDD/SPEC_011_MOTOR_BACKTESTING/SPEC.md` | Criado |
| `docs/SDD/SPEC_011_MOTOR_BACKTESTING/tasks_status.json` | Criado |
| `docs/SDD/SPEC_011_MOTOR_BACKTESTING/spec_status_update.md` | Criado |
| `docs/SDD/README.md` | Modificado — linha SPEC_011 |

---

## 9. Definition of Done

- [x] `BacktestEngine` implementado com INV-011-01 a 05
- [x] CLI funcional com saída JSON
- [x] `GET /backtest` retorna 200/422/503 corretamente
- [x] TEST_011_01 a 06 passando
- [x] `pytest tests/ --tb=short -q` sem falhas
- [x] `ruff check src/ tests/` limpo nos arquivos SPEC_011
- [x] `docs/SDD/README.md` atualizado
