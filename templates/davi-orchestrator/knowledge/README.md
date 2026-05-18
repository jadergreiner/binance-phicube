# Davi Shared Knowledge

Canonical shared knowledge for Davi must live here, close to Davi
specification and orchestration policies.

## Source of Truth

- Canonical knowledge: `templates/davi-orchestrator/core/knowledge/packs/`
- Canonical rules table: `core/knowledge/packs/rules-catalog.knowledge.md`
- SDD cycle artifacts under `docs/sdd-cycles/` are evidence and session history.

Project-specific knowledge is not stored here by default.
It should live inside each consumer repository under:

- `.davi/project-knowledge/business/`
- `.davi/project-knowledge/architecture/`
- `.davi/project-knowledge/governance/`

## Promotion Rule

When new knowledge is approved during refinement:

1. Capture evidence in SDD cycle artifacts.
2. Promote approved knowledge to canonical packs in `core/knowledge/packs/`.
3. Add traceability back to cycle id and file path.
