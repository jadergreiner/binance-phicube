<!-- Context: project-intelligence/technical | Priority: high | Version: 1.0 | Updated: 2025-01-12 -->

# Technical Domain

> Document the technical foundation, architecture, and key decisions.

## Quick Reference

- **Purpose**: Understand how the project works technically
- **Update When**: New features, refactoring, tech stack changes
- **Audience**: Developers, DevOps, technical stakeholders

## Primary Stack

| Layer | Technology | Version | Rationale |
|-------|-----------|---------|-----------|
| Language | [e.g., TypeScript] | [Version] | [Why this language] |
| Framework | [e.g., Node.js] | [Version] | [Why this framework] |
| Database | [e.g., PostgreSQL] | [Version] | [Why this database] |
| Infrastructure | [e.g., AWS, Vercel] | [N/A] | [Why this infra] |
| Key Libraries | [List important ones] | [Versions] | [Why each matters] |

## Architecture Pattern

```
Type: [Monolith | Microservices | Serverless | Agent-based | Hybrid]
Pattern: [Brief description]
Diagram: [Link to architecture diagram if exists]
```

### Why This Architecture?

[Explain the business and technical reasons for this architecture choice. What problem does this architecture solve? What were alternatives considered?]

## Project Structure

```
[Project Root]
├── src/                    # Source code
├── tests/                  # Test files
├── docs/                   # Documentation
├── scripts/                # Build/deploy scripts
└── [Other key directories]
```

**Key Directories**:
- `src/` - Contains all application logic organized by [module/feature/domain]
- `tests/` - [How tests are organized]
- `docs/` - [What documentation lives here]

## Key Technical Decisions

| Decision | Rationale | Impact |
|----------|-----------|--------|
| SimulatedBinanceClient | Testnet Futures geobloqueada no Brasil | Paper trading com dados reais, 42 testes, 320 linhas |
| SPEC_023 fechado | 5/5 tasks, cobertura 81%, soak 48h | MVP validado operacionalmente |

See `decisions-log.md` for full decision history with alternatives.

## SimulatedBinanceClient

**Propósito**: Substitui a Binance Testnet Futures para simulação de trades.

**Arquitetura**:
- Delega dados públicos (OHLCV, ticker, open interest) ao `BinanceClient` real via CCXT
- Simula localmente: ordens (limit/market/SL/TP), posições, saldo, slippage (0.02%)
- PnL calculado no fechamento da posição; margem retornada na redução
- 42 testes em 9 classes (`tests/exchange/test_simulated_client.py`)
- Modo ativado por `SIMULATION_MODE=True` no `.env`
- Usa `SIMULATION_INITIAL_BALANCE` (padrão: 10_000 USDT)

**Files**: `src/exchange/simulated_client.py`, `docker-compose.simulation.yml`, `tests/exchange/test_simulated_client.py`

## SPEC_023 — Validação Operacional

**Status**: 5/5 tasks concluídas.

| Task | Status | Evidência |
|------|--------|-----------|
| Cobertura >80% | ✅ | 80.99% (3578/4418 linhas) |
| 489 testes passando | ✅ | `pytest` exit code 0 |
| Simulação funcional | ✅ | 42 testes, 9 classes |
| Validação 48h soak | ✅ | Orchestrator detecta startup + loop + 3 símbolos |
| Auditoria de ordens | ✅ | 5/5 tasks_status "done" |

**Files**: `scripts/spec_023/`, `docs/SDD/SPEC_023_FECHAMENTO_GAPS_PRD_MVP_OKR/`, `reports/mvp_status_report.md`

## Integration Points

| System | Purpose | Protocol | Direction |
|--------|---------|----------|-----------|
| [API 1] | [What it does] | [REST/GraphQL/gRPC] | [Inbound/Outbound] |
| [Database] | [What it stores] | [PostgreSQL/Mongo/etc] | [Internal] |
| [Service] | [What it provides] | [HTTP/gRPC] | [Outbound] |

## Technical Constraints

| Constraint | Origin | Impact |
|------------|--------|--------|
| [Legacy systems] | [Business/Tech] | [What limitation it creates] |
| [Compliance] | [Regulation] | [What must be followed] |
| [Performance] | [SLAs] | [What must be met] |

## Development Environment

```
Setup: [Quick setup command or link]
Requirements: [What developers need installed]
Local Dev: [How to run locally]
Testing: [How to run tests]
```

## Deployment

```
Environment: [Production/Staging/Development]
Platform: [Where it deploys]
CI/CD: [Pipeline used]
Monitoring: [Tools for observability]
```

## Onboarding Checklist

- [ ] Know the primary tech stack
- [ ] Understand the architecture pattern and why it was chosen
- [ ] Know the key project directories and their purpose
- [ ] Understand major technical decisions and rationale
- [ ] Know integration points and dependencies
- [ ] Be able to set up local development environment
- [ ] Know how to run tests and deploy

## Related Files

- `business-domain.md` - Why this technical foundation exists
- `business-tech-bridge.md` - How business needs map to technical solutions
- `decisions-log.md` - Full decision history with context
