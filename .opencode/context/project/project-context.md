<!-- Context: project/project-context | Priority: high | Version: 1.0 | Updated: 2026-05-10 -->

# Binance Phicube

**O que é**: Bot de auto trade para Binance Futures USDT-M com estratégia BO Williams.
**Stack**: Python 3.12+, asyncio, CCXT (exchange), MongoDB (storage), FastAPI (dashboard), Docker.

---

## Arquitetura

Dois processos `asyncio` independentes:

**Bot** (`src/main.py`): loops de 5 min por par (symbol+timeframe). Fluxo: candles → SignalEngine → RiskManager → OrderManager → MongoRepository + Notifier.

**Dashboard API** (`src/api/main.py`): FastAPI read-only com `DashboardClient` próprio. Fallback `OfflinePositionStream` se falhar.

**Simulação**: `SimulatedBinanceClient` substitui Testnet (geobloqueada no Brasil). Paper trading com dados reais de mercado.

---

## Módulos-Chave

| Módulo | Arquivo | Função |
|--------|---------|--------|
| Exchange | `src/exchange/binance_client.py` | CCXT async, dados públicos + ordens |
| Simulação | `src/exchange/simulated_client.py` | Paper trading (320 linhas, 42 testes) |
| Estratégia | `src/strategy/signal_engine.py` | BO Williams (alligator + fractal + AO) |
| Execução | `src/trading/order_manager.py` | Ordens, SL/TP, gestão de posição |
| Armazenamento | `src/storage/repository.py` | MongoDB via motor |
| Notificação | `src/notifications/` | Telegram ou NullNotifier |
| Config | `src/config/settings.py` | Pydantic BaseSettings (`.env`) |

---

## Comandos Rápidos

```bash
pip install -e ".[dev]"      # instalar dev deps
pytest                        # suite completa (489 testes)
ruff check src/ tests/        # lint (line-length=100)
ruff format src/ tests/       # formatação
python -m src.main            # rodar bot
phicube                       # mesmo que acima (CLI)
uvicorn src.api.main:app      # dashboard (porta 8080)
docker compose up -d          # full stack
docker compose logs -f phicube  # logs do bot
```

---

## Qualidade & Segurança

- **Cobertura >80%** — gate CI em `.github/workflows/spec023-validation.yml`
- **Async-first** — nunca misturar sync/async
- **Risk-first** — SL enviado antes de abrir posição; SL nunca recolocado automaticamente
- **Logging** — `structlog`, nunca `print` ou `logging.basicConfig`
- **Idioma** — pt-BR em código/comentários/logs; commits em inglês (Conventional Commits)

---

## Tópicos Relacionados

- `project-intelligence/decisions-log.md` — Decisões arquiteturais
- `project-intelligence/technical-domain.md` — Detalhamento técnico
- `project-intelligence/living-notes.md` — Issues ativas e aprendizados
- `project-intelligence/business-domain.md` — Contexto de negócio
- `../AGENTS.md` — Guia operacional do agente
- `../docs/SDD/SPEC.md` — Especificação técnica
- `../PRD.md` — Requisitos de produto
