<!-- Context: core/essential-patterns | Priority: critical | Version: 1.1 | Updated: 2026-05-10 -->

# Essential Patterns — Core Development Guidelines

**Core Philosophy**: Modular, Functional, Maintainable.

---

## Critical Patterns

| Pattern | Rule |
|---------|------|
| **Pure Functions** | Same input → same output. No side effects. No mutation of external state. Predictable and testable. |
| **Error Handling** | Catch specific errors. Log with context. Return meaningful messages. **Never** expose internals. |
| **Input Validation** | Check for null/None. Validate types, ranges, constraints. Sanitize user input. Clear error messages. |
| **Security** | **Never** hardcode secrets. Use env vars. Sanitize all input. Use parameterized queries. Escape output. |
| **Logging** | Debug (dev details) / Info (milestones) / Warning (potential issues) / Error (failures). Consistent levels. |

---

## Code Structure

- **Modular**: Single responsibility per module, clear interfaces, composable, <100 lines per component
- **Functional**: Pure functions, immutability, composition over inheritance, declarative style
- **Testable**: Unit tests for pure functions, integration tests for components, edge cases + error conditions

**Anti-Patterns**:
- Deep nesting (>3 levels)
- God modules (>200 lines)
- Global state
- Large functions (>50 lines)
- Hardcoded values
- Tight coupling

---

## Security Anti-Patterns

- Hardcoded credentials
- Exposed sensitive data in logs
- Unvalidated user input
- SQL injection / XSS vulnerabilities

---

## Documentation

- Public APIs, complex logic, non-obvious decisions, usage examples
- Explain **WHY**, not just WHAT
- Keep current, use consistent formatting

---

## Quick Checklist (pre-commit)

- ✅ Pure functions (no side effects)
- ✅ Input validation + error handling
- ✅ No hardcoded secrets
- ✅ Tests written and passing
- ✅ Documentation updated

---

## Related

- `standards/code-quality.md` — Comprehensive code standards
- `standards/security-patterns.md` — Security pattern catalog
- `standards/test-coverage.md` — Testing best practices
- `standards/documentation.md` — Documentation guidelines
- `standards/code-analysis.md` — Code analysis framework
- `workflows/code-review.md` — Code review process
