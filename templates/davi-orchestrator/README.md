# Davi Orchestrator Template

Portable two-stage framework for product evolution across projects.

## Repository Boundary (Mandatory)

- Agent organization and rules belong only to `jadergreiner/agent-davi`.
- Consumer repositories only use Davi.
- Project-specific knowledge stays in each consumer project.
- Davi provides a reusable standard structure for consumers.

## Model

1. Stage 1 - Refiners:

- Define scope, specs, constraints, acceptance criteria.
- Must not implement code.

1. Stage 2 - Executors:

- Implement exactly what Stage 1 approved.
- Can propose changes, but cannot change scope without a new refinement gate.

## Davi Role

Davi is the orchestrator:

- Classifies each request.
- Routes to Refiner or Executor.
- Enforces gates between stages.
- Blocks coding until refinement is approved.

## Folder Structure

- `prompts/davi.base.prompt.md`: reusable Davi core prompt.
- `context/project.context.template.yaml`: project-local customization fields.
- `workflow/two-stage.policy.md`: governance and gates.
- `workflow/repository-boundary.policy.md`:
  ownership boundary between agent core and consumer projects.
- `workflow/routing-rules.md`: routing logic and status messages.
- `workflow/intake-paths.policy.md`: entry paths (Q&A, RCA, New Implementation).
- `workflow/knowledge-gate.policy.md`: mandatory knowledge check before path selection.
- `workflow/artifact-lint-gate.policy.md`:
  mandatory lint gate for created/edited artifacts.
- `core/knowledge/packs/rules-catalog.knowledge.md`:
  canonical table of rules with incremental IDs (RNxx).
- `workflow/lint-evidence.template.md`:
  template for lint execution evidence records.
- `workflow/knowledge-gate.response-templates.md`:
  standardized first response templates for Adherent,
  Divergent, and No Knowledge cases.
- `core/`: canonical Davi core assets (rules, packs, governance).
- `consumer/`: templates and contracts for consumer repository usage.
- `refiners/`: three-layer refiner model (business, architecture, governance).
- `executors/`: six execution profiles (E1..E6), flow, and governance.
- `sdd/`: six-stage SDD flow with formal approval gate per stage.
- `specs/refiner-spec.template.md`: required output from Stage 1.
- `handoff/refiner-to-executor.checklist.md`: completeness gate.
- `execution/executor-task.template.md`: Stage 2 implementation contract.
- `qa/acceptance.template.md`: validation template after implementation.

## Quick Start

1. Keep Davi core rules in `agent-davi` as source of truth.
2. In each consumer project, create only project-specific knowledge folders:
   - `.davi/project-knowledge/business/`
   - `.davi/project-knowledge/architecture/`
   - `.davi/project-knowledge/governance/`
   - reference: `consumer/project-knowledge/structure.template.md`
3. Fill `context/project.context.template.yaml` for project context.
4. Use `prompts/davi.base.prompt.md` as the agent system prompt.
5. Start every request through Davi routing (`workflow/routing-rules.md`).
6. Do not code until the Refiner spec is approved and checklist passes.

## Activation Rule

When the user calls `Davi`, answer as Davi and apply routing immediately.
