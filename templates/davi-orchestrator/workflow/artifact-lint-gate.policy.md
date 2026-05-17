# Artifact Lint Gate Policy

Mandatory quality gate for artifact creation and editing.

## Trigger

Run this gate whenever a tracked artifact is created or modified.

## Scope (minimum)

- Markdown (`*.md`)
- YAML (`*.yml`, `*.yaml`) when present

## Default Commands

- Markdown:
  - `markdownlint <paths>`
  - `markdownlint --fix <paths>` when autofix is available
- YAML:
  - `yamllint <paths>` when available
  - If `yamllint` is not available, run syntax parse validation

## Decision Rule

- PASS:
  - All lint checks pass after autofix/revalidation.
- FAIL:
  - Any remaining lint error blocks progression.

## Blocking Behavior

- Do not advance SDD stage approval while lint is FAIL.
- Do not hand off to Executor while lint is FAIL.
- Do not finalize commit while lint is FAIL.

## Evidence Record (required)

- Timestamp
- SDD cycle id (if applicable)
- Paths checked
- Commands executed
- Result (`PASS` or `FAIL`)
- Remaining issues (if any)
