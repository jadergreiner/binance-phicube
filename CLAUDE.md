# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Run Tests
```bash
pytest                                              # full suite
pytest tests/test_signal_engine.py -v              # single file
pytest tests/test_signal_engine.py::TestClass::test_name -v  # single test
pytest tests/ -v --tb=short                        # verbose with short tracebacks
```

### Lint / Format
```bash
ruff check src/ tests/
ruff format src/ tests/
```

### Run Locally
```bash
pip install -e .
python -m src.main          # trading bot
uvicorn src.api.main:app --host 0.0.0.0 --port 8080  # dashboard API
```

### Docker (full stack)
```bash
docker compose up -d                        # bot + api + mongo
docker compose --profile dev up -d         # adds mongo-express on :8081
docker compose logs -f phicube
docker compose down
```

## Architecture

The system has two independent runtime processes:

1. **Trading Bot** (`src/main.py`) — `TradingMonitor` instances, one per `(symbol, timeframe)` pair, each running an infinite loop every 5 minutes via `asyncio.gather()`.

2. **Dashboard API** (`src/api/main.py`) — FastAPI app (`uvicorn`) serving a read-only position dashboard on port 8080. Completely separate from the bot process; communicates with Binance via its own `DashboardClient` and with the database via `MongoRepository`.

### Core Bot Flow

```
BinanceClient (CCXT async)
    └─ TradingMonitor.run() [every 5 min]
        ├─ Fetch OHLCV candles (drop last incomplete)
        ├─ SignalEngine.evaluate() → Long / Short / None
        ├─ Guard: skip if symbol already open or max_open_positions reached
        ├─ RiskManager.calculate() → position size
        ├─ OrderManager.execute() → Trade (entry + SL + TP orders)
        ├─ MongoRepository.save_trade()
        └─ Notifier.send() (TelegramNotifier or NullNotifier)
```

### Key Components

| Module | Responsibility |
|--------|---------------|
| `src/config/settings.py` | Pydantic `BaseSettings`; `get_settings()` cached with `@lru_cache` |
| `src/exchange/binance_client.py` | CCXT async wrapper for Binance Futures USDT-M |
| `src/strategy/signal_engine.py` | BO Williams Phicube signal detection (Alligator + AO + Fractals) |
| `src/strategy/indicators.py` | Technical indicator calculations |
| `src/trading/order_manager.py` | Order execution + `Trade` / `TradeStatus` dataclasses |
| `src/trading/risk_manager.py` | Position size from risk % and account balance |
| `src/storage/repository.py` | MongoDB async (motor): trades, signals, audit collections |
| `src/notifications/` | `Notifier` ABC → `TelegramNotifier` / `NullNotifier` |
| `src/dashboard/` | `DashboardClient`, `PositionStream`, `AdaptiveUpdater` for the UI |
| `src/api/routes/` | FastAPI routers: `positions`, `performance` |

### MongoDB Collections

- `trades` — executed trades (entry/SL/TP order IDs, status, PnL fields)
- `signals` — all signals detected, regardless of execution
- `audit` — immutable action log

### Notification Pattern

`Notifier` is an abstract base; `_create_notifier(settings)` returns `TelegramNotifier` when both `TELEGRAM_TOKEN` and `TELEGRAM_CHAT_ID` are set, otherwise `NullNotifier`. **Security invariant: the Telegram token must never appear in logs** — use `type(exc).__name__` not `str(exc)` when logging `aiohttp.ClientError` (the URL with token is embedded in the exception message).

### Dashboard Fallback

If the `DashboardClient` or `PositionStream` fails to initialize, the API falls back to `OfflinePositionStream` — it still serves the UI with degraded data rather than crashing.

## Development Conventions

- **Language**: All docstrings, comments, variable names, and log messages in Brazilian Portuguese (pt-BR). Commit messages follow Conventional Commits in English (`feat:`, `fix:`, `docs:`, `refactor:`).
- **Async-first**: Entire codebase is `asyncio`-based. Never mix sync and async; use `asyncio.run()` at entry points only.
- **Structured logging**: Use `structlog` exclusively — never `print` or `logging.basicConfig`.
- **Testnet by default**: Set `BINANCE_TESTNET=True` in `.env` during development.
- **Risk-first**: No position may open without a stop-loss order already placed.
- **Spec-driven development**: New features follow SPEC → Task Graph → Implementation → Validation. See `docs/SDD/` for all SPECs and `docs/SDD/MCP_SERENA_FLOW.md` for the pipeline.

## Configuration

All runtime configuration comes from environment variables validated by `src/config/settings.py`. Copy `.env.example` to `.env`. Key variables:

- `BINANCE_API_KEY` / `BINANCE_API_SECRET` — futures trading credentials
- `DASHBOARD_API_KEY` / `DASHBOARD_API_SECRET` — separate read-only credentials for the dashboard
- `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` — optional; notifications disabled if absent
- `MONGODB_URI` — defaults to `mongodb://mongo:27017`

