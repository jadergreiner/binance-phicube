---
name: security-threat-model
description: Repository-grounded threat modeling for Phicube. Use when you need to map trust boundaries, assets, attacker goals, abuse paths, and concrete mitigations for this codebase or a specific path.
---

# Security Threat Model

Generate an actionable threat model grounded in this repository, not a generic checklist.

## When To Use

- Before production release checkpoints
- When adding new external integrations or credentials
- When changing API exposure, auth flows, or Docker/network settings
- When investigating security incidents

## Quick Start

Run:

```bash
python .codex/skills/security-threat-model/scripts/generate_threat_model.py --repo . --overwrite
```

Optional output path:

```bash
python .codex/skills/security-threat-model/scripts/generate_threat_model.py --repo . --output reports/threat-models/custom-threat-model.md --overwrite
```

## Workflow

1. Generate the baseline threat model document with the script.
2. Review the generated trust boundaries and assets.
3. Validate threats and mitigations with `security-audit` findings.
4. Turn high-risk mitigations into tracked tasks.

## Required Output

The final Markdown must include:

- Scope and assumptions
- System boundaries and data flows
- Key assets and threat actors
- Prioritized STRIDE threats
- Concrete mitigations and follow-up actions

