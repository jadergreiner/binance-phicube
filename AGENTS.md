# AGENTS.md

Guia operacional para agentes no repositório Binance Phicube.

Projeto: bot de auto trade **Binance Futures USDT-M**, estratégia **BO Williams (Alligator SMMA + Awesome Oscillator + Fractais de 5 barras)**.

## Idioma

- Código, comentários, docstrings, logs: **pt-BR**
- Commits: **inglês** (Conventional Commits: `feat:`, `fix:`, `refactor:`, `docs:`)

## Comandos

```bash
pip install -e ".[dev]"             # instala com dev deps
pytest                               # suite completa
pytest tests/<path> -v               # arquivo ou teste específico
pytest tests/ -v --tb=short          # verbose com traceback curto
ruff check src/ tests/                # lint (line-length=100, select E/F/I/UP)
ruff format src/ tests/               # formatação
python -m src.main                    # executar bot
phicube                               # mesmo que acima (entrypoint em pyproject.toml)
python tools/phicube_ops_cli.py doctor --json   # diagnóstico operacional
```

### Dashboard API (processo separado)

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 8080
```

### Docker (full stack)

```bash
docker compose up -d                  # bot + dashboard-api + mongo
docker compose --profile dev up -d    # + mongo-express em :8081
docker compose logs -f phicube        # logs do bot
docker compose down                   # derruba tudo
```

## Arquitetura

Dois processos `asyncio` independentes:

1. **Bot** (`src/main.py`) — loop de 5 min por par (symbol+timeframe). `TradingMonitor` por par, executa `_tick()` a cada candle fechada. Fluxo: fetch OHLCV (descarta última candle incompleta) → `SignalEngine.evaluate()` → `RiskManager.calculate()` → `OrderManager.execute()` → `MongoRepository.save_trade()` + `Notifier.send()`.
2. **Dashboard API** (`src/api/main.py`) — FastAPI read-only em :8080. `DashboardClient` próprio (credencial separada, somente leitura). Fallback `OfflinePositionStream` se falhar.

O bot também inicia um **health server** HTTP mínimo em :8081 para Docker healthcheck (SPEC_017).

### Componentes-chave

| Módulo | Responsabilidade |
|--------|-----------------|
| `src/config/settings.py` | Pydantic `BaseSettings` + `@lru_cache` em `get_settings()`. Lê `.env`. |
| `src/exchange/binance_client.py` | CCXT async, Futures USDT-M |
| `src/exchange/simulated_client.py` | Paper trading local (modo simulação) |
| `src/strategy/signal_engine.py` | Alligator + AO + Fractals → Direction.LONG/SHORT/None |
| `src/strategy/indicators.py` | SMMA, AO, Fractais (pandas/numpy puro) |
| `src/trading/order_manager.py` | Market entry + OCO (STOP_MARKET + TAKE_PROFIT_MARKET) |
| `src/trading/risk_manager.py` | Position size a partir de risco % + saldo |
| `src/storage/repository.py` | MongoDB async (motor): coleções `trades`, `signals`, `audit` |
| `src/notifications/` | ABC `Notifier` → `TelegramNotifier` / `NullNotifier` |

### Configuração (`src/config/settings.py`)

Tudo via `.env`. Schema canônico de pares: `SYMBOL:TIMEFRAME:LEVERAGE` separado por vírgula (ex: `BTCUSDT:15m:5,ETHUSDT:15m:5`). Ver `.env.example` para todas as variáveis.

### MongoDB

Três coleções: `trades` (operações executadas), `signals` (todos os sinais detectados), `audit` (log imutável de ações).

## Convenções e segurança

- **Async-first**: nunca misturar sync/async. `asyncio.run()` só nos entrypoints.
- **Windows**: `entrypoint()` em `src/main.py` já aplica `WindowsSelectorEventLoopPolicy()` — não sobrescrever.
- **Logging**: `structlog`. Nunca usar `print` ou `logging.basicConfig`.
- **Telegram token**: nunca logar `str(exc)` de `aiohttp.ClientError` (a URL com token vem na mensagem). Usar `type(exc).__name__`.
- **Risk-first**: nenhuma posição abre sem stop-loss já enviado. SL nunca é recolocado automaticamente.
- **Testnet default**: `BINANCE_TESTNET=True` em desenvolvimento.
- **Simulação**: `SIMULATION_MODE=true` ativa `SimulatedBinanceClient` (execução local sem ordens reais, mas dados reais de mercado).
- **Spec-driven**: novas features em `docs/SDD/SPEC.md` e `docs/SDD/<SPEC_N>/SPEC.md`.

## Testes

- `pytest` com `asyncio_mode = auto` (config em `pyproject.toml`)
- Cobertura mínima **80%** — gate no CI (`spec023-validation.yml`)
- `tests/<categoria>/` espelha `src/` (ex: `tests/strategy/`, `tests/trading/`, `tests/api/`)

## CI

Duas workflows acionadas em PR:
- **spec023-validation**: cobertura ≥ 80% + validação de estrutura + gates operacionais (workflow_dispatch)
- **spec021-validation**: quality gate + hardening + soak evidence

## Skills do projeto

- `skills/` — skills legadas (git-commit-push, lint-on-edit, qa-review, security-audit, signal-review, markdown-lint-on-edit, sdd-spec-driven-development)
- `.opencode/skills/` — skills OpenCode (task-management, create-plan, changelog-generator, etc.)

## Fontes de verdade canônicas

- Config: `.env` → `src/config/settings.py` (Pydantic)
- SPEC: `docs/SDD/SPEC.md` (especificação técnica geral) + `docs/SDD/<SPEC_N>/SPEC.md` (por feature)
- PRD: `PRD.md` — requisitos de produto
- OpenSpec CLI: `openspec new change`, `openspec validate`, `openspec archive`
- Rotação de segredos: `docs/OPERATIONS.md`
- Diagnóstico: `python tools/phicube_ops_cli.py doctor --json`
