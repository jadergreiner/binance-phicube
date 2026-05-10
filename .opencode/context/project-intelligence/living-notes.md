<!-- Context: project-intelligence/notes | Priority: high | Version: 1.0 | Updated: 2025-01-12 -->

# Living Notes

> Active issues, technical debt, open questions, and insights that don't fit elsewhere. Keep this alive.

## Quick Reference

- **Purpose**: Capture current state, problems, and open questions
- **Update**: Weekly or when status changes
- **Archive**: Move resolved items to bottom with status

## Technical Debt

| Item | Impact | Priority | Mitigation |
|------|--------|----------|------------|
| [Debt item] | [What risk it creates] | [High/Med/Low] | [How to manage] |

### Technical Debt Details

**[Debt Item]**  
*Priority*: [High/Med/Low]  
*Impact*: [What happens if not addressed]  
*Root Cause*: [Why this debt exists]  
*Proposed Solution*: [How to fix it]  
*Effort*: [Small/Medium/Large]  
*Status*: [Acknowledged | Scheduled | In Progress | Deferred]

## Open Questions

| Question | Stakeholders | Status | Next Action |
|----------|--------------|--------|-------------|
| [Question] | [Who needs to decide] | [Open/In Progress] | [What needs to happen] |

### Open Question Details

**[Question]**  
*Context*: [Why this question matters]  
*Stakeholders*: [Who needs to be involved]  
*Options*: [What are the possibilities]  
*Timeline*: [When does this need resolution]  
*Status*: [Open/In Progress/Blocked]

## Known Issues

| Issue | Severity | Workaround | Status |
|-------|----------|------------|--------|
| [Issue] | [Critical/High/Med/Low] | [Temporary fix] | [Known/In Progress/Fixed] |

### Issue Details

**[Issue Title]**  
*Severity*: [Critical/High/Med/Low]  
*Impact*: [Who/what is affected]  
*Reproduction*: [Steps to reproduce if applicable]  
*Workaround*: [Temporary solution if exists]  
*Root Cause*: [If known]  
*Fix Plan*: [How to properly fix]  
*Status*: [Known/In Progress/Fixed in vX.X]

## Insights & Lessons Learned

### What Works Well
- [Positive pattern 1] - [Why it works]
- [Positive pattern 2] - [Why it works]

### What Could Be Better
- [Area for improvement 1] - [Why it's a problem]
- [Area for improvement 2] - [Why it's a problem]

### Lessons Learned
- **Blocos bloqueantes dentro de try/except viram loop infinito** — `sleep()` dentro de `try/except Exception` no `HeartbeatTask` fazia o heartbeat disparar sem pausa se o MongoDB desconectasse. Fix: mover `sleep` para fora do bloco try.
- **Logs de bibliotecas terceiras podem dominar o output** — pymongo produziu 94k linhas em 37min em modo WARNING. Fix: `setLevel(logging.WARNING)` no logger do pymongo.
- **Simulação > Testnet quando geobloqueada** — paper trading com dados reais de mercado via `SimulatedBinanceClient` é mais controlável e igualmente válido para validação.

## Patterns & Conventions

### Code Patterns Worth Preserving
- [Pattern 1] - [Where it lives, why it's good]
- [Pattern 2] - [Where it lives, why it's good]

### Gotchas for Maintainers
- **Nunca colocar `sleep()`/`await` dentro de `try/except` genérico** — se a exceção for capturada, o loop continua infinitamente sem pausa, causando CPU 100% e log flood. Exemplo (fixo): `heartbeat_task.py` — `sleep` foi movido para fora do `try/except`.
- **Pymongo loga 94k+ linhas em 37min em WARNING** — sempre configurar `logging.getLogger("pymongo").setLevel(logging.WARNING)` após conectar. Feito em `src/monitoring/logger.py`.
- **MongoDB port exposta** em `docker-compose.simulation.yml` (`127.0.0.1:27017`) — só acessível localmente, mas nunca expor em produção.

## Active Projects

| Project | Goal | Owner | Timeline |
|---------|------|-------|----------|
| MVP Simulation + SPEC_023 | Paper trading funcional, cobertura >80%, 48h soak | Time dev | Concluído (2026-05-10) |

## Archive (Resolved Items)

Moved here for historical reference. Current team should refer to current notes above.

### Resolved: [Item]
- **Resolved**: [Date]
- **Resolution**: [What was decided/done]
- **Learnings**: [What we learned from this]

## Onboarding Checklist

- [ ] Review known technical debt and understand impact
- [ ] Know what open questions exist and who's involved
- [ ] Understand current issues and workarounds
- [ ] Be aware of patterns and gotchas
- [ ] Know active projects and timelines
- [ ] Understand the team's priorities

## Related Files

- `decisions-log.md` - Past decisions that inform current state
- `business-domain.md` - Business context for current priorities
- `technical-domain.md` - Technical context for current state
- `business-tech-bridge.md` - Context for current trade-offs
