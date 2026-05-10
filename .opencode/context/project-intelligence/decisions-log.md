<!-- Context: project-intelligence/decisions | Priority: high | Version: 1.0 | Updated: 2025-01-12 -->

# Decisions Log

> Record major architectural and business decisions with full context. This prevents "why was this done?" debates.

## Quick Reference

- **Purpose**: Document decisions so future team members understand context
- **Format**: Each decision as a separate entry
- **Status**: Decided | Pending | Under Review | Deprecated

## Decision Template

```markdown
## [Decision Title]

**Date**: YYYY-MM-DD
**Status**: [Decided/Pending/Under Review/Deprecated]
**Owner**: [Who owns this decision]

### Context
[What situation prompted this decision? What was the problem or opportunity?]

### Decision
[What was decided? Be specific about the choice made.]

### Rationale
[Why this decision? What were the alternatives and why were they rejected?]

### Alternatives Considered
| Alternative | Pros | Cons | Why Rejected? |
|-------------|------|------|---------------|
| [Alt 1] | [Pros] | [Cons] | [Why not chosen] |
| [Alt 2] | [Pros] | [Cons] | [Why not chosen] |

### Impact
**Positive**: [What this enables or improves]
**Negative**: [What trade-offs or limitations this creates]
**Risk**: [What could go wrong]

### Related
- [Links to related decisions, PRs, issues, or documentation]
```

---

## Decision: [Title]

**Date**: YYYY-MM-DD
**Status**: [Status]
**Owner**: [Owner]

### Context
[What was happening? Why did we need to decide?]

### Decision
[What we decided]

### Rationale
[Why this was the right choice]

### Alternatives Considered
| Alternative | Pros | Cons | Why Rejected? |
|-------------|------|------|---------------|
| [Option A] | [Good things] | [Bad things] | [Reason] |
| [Option B] | [Good things] | [Bad things] | [Reason] |

### Impact
- **Positive**: [What we gain]
- **Negative**: [What we trade off]
- **Risk**: [What to watch for]

### Related
- [Link to PR #000]
- [Link to issue #000]
- [Link to documentation]

---

## Decision: Simulation Mode > Binance Testnet

**Date**: 2026-05-10
**Status**: Decided
**Owner**: Time dev

### Context
Binance Testnet Futures é geobloqueado no Brasil — conexões retornam erro de região. O projeto precisava de um ambiente de validação operacional (SPEC_023) que exigia 50+ trades simulados e 48h de soak.

### Decision
Criar `SimulatedBinanceClient` que substitui a Testnet: delega dados públicos (OHLCV, ticker, open interest) ao `BinanceClient` real via CCXT, mas simula ordens, posições, SL/TP, saldo e slippage localmente. Nenhuma ordem real é enviada.

### Rationale
- Testnet geobloqueada sem previsão de liberação
- Solução de paper trading própria elimina dependência externa
- Usa dados reais de mercado (preço, volume, OI) → simulação realista
- MongoDB continua recebendo dados → scripts de auditoria funcionam
- Código 100% versionado, sem chaves de testnet

### Alternatives Considered
| Alternative | Pros | Cons | Why Rejected? |
|-------------|------|------|---------------|
| VPN para Testnet | Acesso imediato | Latência, dependência externa, custo | Complexidade operacional desnecessária |
| Only-read Binance + cálculos manuais | Simples | Sem validação de execução | Não atende SPEC_023 |
| Mock completo (sem dados reais) | Isolamento total | Preços irreais, sem validade | Dados sintéticos não validam estratégia real |

### Impact
- **Positive**: Ambiente de simulação completo, reprodutível, versionado. Qualquer dev roda `docker compose -f docker-compose.simulation.yml up` e tem o ecossistema completo.
- **Negative**: Slippage fixo (0.02%) não captura variações de liquidez. Sem latência de rede simulada.
- **Risk**: Se `SIMULATION_MODE=True` for acidentalmente usado em produção, ordens reais não são enviadas (seguro por design).

### Related
- `src/exchange/simulated_client.py` — 320 linhas, 42 testes
- `docker-compose.simulation.yml` — override Docker
- `docs/SDD/SPEC_023_FECHAMENTO_GAPS_PRD_MVP_OKR/` — SPEC original

---

## Deprecated Decisions

Decisions that were later overturned (for historical context):

| Decision | Date | Replaced By | Why |
|----------|------|-------------|-----|
| [Old decision] | [Date] | [New decision] | [Reason] |

## Onboarding Checklist

- [ ] Understand the philosophy behind major architectural choices
- [ ] Know why certain technologies were chosen over alternatives
- [ ] Understand trade-offs that were made
- [ ] Know where to find decision context when questions arise
- [ ] Understand what decisions are pending and why

## Related Files

- `technical-domain.md` - Technical implementation affected by these decisions
- `business-tech-bridge.md` - How decisions connect business and technical
- `living-notes.md` - Current open questions that may become decisions
