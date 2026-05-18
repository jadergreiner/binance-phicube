# Repository Boundary Policy

Defines ownership boundaries between Davi core and consumer projects.

## Ownership Model

- Davi core organization and rules are owned by `agent-davi`.
- Consumer repositories are users of Davi core.
- Consumer repositories own only project-specific knowledge.

## Davi Core (agent-davi)

Must stay in `agent-davi`:

- Orchestration prompts and routing policies
- Refiner/Executor contracts and gates
- SDD protocol and templates
- Canonical cross-project rule catalog
- Canonical knowledge packs under `templates/davi-orchestrator/core/knowledge/packs/`

## Consumer Project

Must stay in each consumer repository:

- Business/architecture/governance specifics of that project
- Local decisions, constraints, and evidence artifacts
- Project-local SDD cycles and implementation evidence

Recommended structure:

- `.davi/project-knowledge/business/`
- `.davi/project-knowledge/architecture/`
- `.davi/project-knowledge/governance/`
- based on `templates/davi-orchestrator/consumer/project-knowledge/structure.template.md`

## Non-Negotiable Rules

- Do not duplicate Davi core governance as local source of truth.
- Do not promote local project knowledge into cross-project canon
  without explicit human approval.
- In divergence between local project constraints and Davi core,
  escalate to human decision before implementation.
