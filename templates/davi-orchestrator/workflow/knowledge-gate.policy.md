# Knowledge Gate Policy

Mandatory entry gate for every request handled by Davi.

## Core Question

Is there current knowledge about the topic in existing artifacts?

## Sources to Check

- Canonical shared packs under `templates/davi-orchestrator/core/knowledge/packs/`
- Project-specific packs under `.davi/project-knowledge/`
- Approved SPECs and task sets

## Outcomes

### Outcome A: Knowledge Exists

Required actions:

1) Assess adherence vs divergence.
2) If adherent, proceed to path classification.
3) If divergent, escalate to human decision and block progression until decision.

Human decision options on divergence:

- Option 1: evolve rules/knowledge to support proposal
- Option 2: adjust proposal to existing rules

### Outcome B: Knowledge Does Not Exist

Required actions:

1) Start Refiner flow to build baseline knowledge.
2) Ask human whether captured knowledge should be promoted to packs.
3) Register approved knowledge in canonical shared packs.
4) Persist SDD artifacts as evidence and collect formal approvals.
5) Then proceed to path classification.

## Non-Negotiable Rules

- Never assume nonexistent knowledge.
- Never auto-resolve divergence without human decision.
- Keep decision traceability in persisted artifacts.
- Use `workflow/knowledge-gate.response-templates.md`
  for the first operational response after gate evaluation.
- Knowledge only in project code or cycle notes is not canonical until
  promoted into shared packs.
- Project-specific knowledge is canonical only inside its own project scope;
  it is not cross-project canonical by default.
