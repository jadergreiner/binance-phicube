# Hardening Checklist - SPEC_021

Status values: `pass`, `fail`, `manual`.

| id | check | type | status | evidence_required |
|---|---|---|---|---|
| HARD-001 | Runtime container uses non-root user (`USER phicube`) | automated | pass/fail | Dockerfile snippet |
| HARD-002 | Runtime container defines `HEALTHCHECK` | automated | pass/fail | Dockerfile snippet |
| HARD-003 | No obvious hardcoded secrets in tracked source/docs (`API_KEY`, `API_SECRET`, `TOKEN`, `PASSWORD`) | automated | pass/fail | scanner report |
| HARD-004 | Operational evidence does not contain secrets | manual | manual | evidence review note |
| HARD-005 | `.env` remains local and not tracked in git | manual | manual | `git status`/repo policy evidence |

## Automated validation output

`reports/spec021_hardening_report.json`

```json
{
  "status": "pass|fail",
  "checks": [
    {"id": "HARD-001", "status": "pass", "details": "..." }
  ],
  "failures": []
}
```
