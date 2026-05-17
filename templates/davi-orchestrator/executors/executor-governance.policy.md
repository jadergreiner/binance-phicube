# Executors Governance Policy

## Human Approval Requirements

- Any scope expansion beyond approved Tasks requires formal human approval.
- Any intentional break of canonical requirements requires formal human approval.
- Any risk-relevant change without mitigation requires explicit human decision.

## Escalation Rules

- E1 escalates blockers immediately when they affect timeline/scope/risk.
- E2/E3/E4 escalate unresolved design/contract/runtime conflicts to E1.
- E6 escalates critical QA failures to E1 and blocks closure.

## Evidence Requirements per Executor

- E1: assignment/handoff log + closure summary
- E2: architecture review report
- E3: data contract impact report
- E4: ML behavior validation report
- E5: task-to-code mapping and execution outputs
- E6: acceptance report with pass/fail decision

## Closure Conditions

- All mandatory gates passed
- Lint gate `PASS`
- Acceptance criteria evaluated
- Final go/no-go decision documented
