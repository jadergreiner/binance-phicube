# Davi Usage in This Repository

This repository is a consumer of Davi.

## Source of Agent Core

- Agent core repository:
  `https://github.com/jadergreiner/agent-davi`
- Ownership of Davi core rules/policies stays in `agent-davi`.

## Local Ownership

This repository owns only project-specific knowledge under:

- `.davi/project-knowledge/business/`
- `.davi/project-knowledge/architecture/`
- `.davi/project-knowledge/governance/`

## Rule of Use

- Do not treat local copies under `templates/davi-orchestrator/` as
  authoritative source of Davi core governance.
- Use local project knowledge + approved SDD/OpenSpec evidence for
  project decisions.
