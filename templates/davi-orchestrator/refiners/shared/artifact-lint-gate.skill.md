# Shared Skill: artifact-lint-gate

## Type

Cross-layer shared skill (Business, Architecture, Governance, SDD artifacts).

## Mission

Run lint automatically on created/edited artifacts, apply autofix when possible,
revalidate, and produce evidence for decision gates.

## Inputs

- Changed artifact paths
- Current SDD cycle id (when applicable)
- Project lint command mapping

## Outputs

- Lint status: `PASS` or `FAIL`
- Checked files list
- Commands executed
- Remaining issues list (if FAIL)
- Evidence log entry

## Rules

- Trigger this skill on any create/edit action for scoped artifacts.
- Apply autofix first when supported, then rerun lint.
- Block stage progression, handoff, and commit while status is `FAIL`.
- Keep output concise and auditable.

## Default Checks

- Markdown: `markdownlint` (`--fix` before final check when available)
- YAML: `yamllint` or parse validation fallback

## Evidence Template

- Timestamp:
- Cycle ID:
- Files:
- Commands:
- Result:
- Remaining issues:
