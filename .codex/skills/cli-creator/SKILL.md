---
name: cli-creator
description: Build or evolve a reusable project CLI for repeated operational tasks (logs, health checks, CI triage, and quality gates). Use when workflows are repeated via ad-hoc shell commands and should be standardized.
---

# CLI Creator (Phicube)

Use this skill to convert repeated operational command sequences into stable CLI commands.

## When To Use

- Repeated Docker log and health checks
- Repeated CI diagnostics commands
- Repeated validation scripts that should be one command

## Current CLI Baseline

Primary entrypoint:

```bash
python tools/phicube_ops_cli.py --help
```

Implemented subcommands:

- `doctor`: verify local prerequisites and skill availability
- `api-health`: probe API health endpoint
- `dashboard-logs`: fetch dashboard-api logs with optional pattern filter
- `ci-inspect`: run the `gh-fix-ci` inspector script for a PR

## Workflow

1. Identify the repeated shell sequence to standardize.
2. Add a dedicated subcommand in `tools/phicube_ops_cli.py`.
3. Keep arguments explicit and safe (no destructive defaults).
4. Add `--json` output for machine-friendly consumption when relevant.
5. Update playbook docs with the new command example.

## Validation

Run:

```bash
python tools/phicube_ops_cli.py doctor --json
python tools/phicube_ops_cli.py --help
```

