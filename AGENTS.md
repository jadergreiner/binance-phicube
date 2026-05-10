# AGENTS.md

Guia operacional para agentes no repositório Binance Phicube.

Projeto: bot de auto trade Binance Futures USDT-M.
Idioma: pt-BR em código, comentários e logs; commits em inglês (Conventional Commits).

## Comandos

```bash
pip install -e ".[dev]"           # instalar dev deps
pytest                             # suite completa
pytest tests/<path> -v            # arquivo ou teste específico
ruff check src/ tests/             # lint (line-length=100, seleção E/F/I/UP)
ruff format src/ tests/            # formatação
python -m src.main                 # bot (entrypoint: src/main.py)
phicube                            # mesmo que acima (CLI installável)
uvicorn src.api.main:app          # dashboard API (porta 8080)
docker compose up -d               # full stack: bot + dashboard-api + mongo
docker compose logs -f phicube     # logs do bot
docker compose down                # derruba tudo
python tools/phicube_ops_cli.py doctor --json   # diagnóstico operacional
```

Cobertura mínima: 80%. Gate CI em `.github/workflows/spec023-validation.yml`.

## Arquitetura

Dois processos independentes, ambos `asyncio`:

1. **Bot** (`src/main.py`) — loops de 5 min por par (symbol+timeframe). Fluxo: candles → SignalEngine → RiskManager → OrderManager → MongoRepository + Notifier.
2. **Dashboard API** (`src/api/main.py`) — FastAPI read-only. `DashboardClient` próprio (credencial separada). Fallback `OfflinePositionStream` se falhar.

Componentes-chave: `src/exchange/binance_client.py` (CCXT async), `src/strategy/signal_engine.py` (BO Williams), `src/trading/order_manager.py` (execução), `src/storage/repository.py` (MongoDB motor), `src/notifications/` (Telegram ou Null).

## Convenções e segurança

- **Async-first**: nunca misturar sync e async. `asyncio.run()` só nos entrypoints.
- **Logging**: `structlog`. Nunca usar `print` ou `logging.basicConfig`.
- **Telegram token**: nunca logar `str(exc)` de `aiohttp.ClientError` (a URL com token vem na mensagem). Usar `type(exc).__name__`.
- **Risk-first**: nenhuma posição abre sem stop-loss já enviado. SL nunca é recolocado automaticamente (DD-002).
- **Testnet default**: `BINANCE_TESTNET=True` em desenvolvimento.
- **Spec-driven**: novas features seguem `docs/SDD/` → ver `docs/SDD/SPEC.md` e `docs/SDD/MCP_SERENA_FLOW.md`.

## Skills do projeto

- `skills/` — 7 skills legadas (git-commit-push, lint-on-edit, qa-review, etc.)
- `.opencode/skills/` — 28 skills replicadas do codex (versionadas no repo)
- `docs/SKILLS_ADOPTION_PLAYBOOK.md` — governança de skills

## Fontes de verdade

- Config: `.env.example` → `src/config/settings.py` (Pydantic BaseSettings + lru_cache)
- SPEC: `docs/SDD/SPEC.md` (especificação técnica)
- PRD: `PRD.md` (requisitos de produto)
- Manisfesto: `MANIFESTO.md` (princípios)
- Revisão de diff: `code_review.md`
- Rotação de segredos: `docs/OPERATIONS.md`
- Governance CLI (canônico): `openspec new change`, `openspec validate`, `openspec archive`
