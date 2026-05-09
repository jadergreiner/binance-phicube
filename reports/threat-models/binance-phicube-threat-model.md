# Threat Model: binance-phicube

Generated: 2026-05-09 13:00 UTC
Repository: `C:\repo\binance-phicube`

## Scope And Assumptions

- Scope: repository-level model for runtime, API, dashboard, CI, and deployment artifacts.
- Assumption: project remains single-tenant and GitHub-centric.
- Assumption: production secrets are injected by environment variables and are not committed.

## System Boundaries

Components in scope:
- Trading bot runtime
- Docker Compose stack
- GitHub Actions workflows
- FastAPI service endpoints
- Dashboard UI and stream updater

Trust boundaries:
- Public internet -> Dashboard/API endpoints
- Application services -> Binance APIs
- Application services -> MongoDB data store
- Operator machine/CI runner -> GitHub repository and workflows

Observed host port mappings: 127.0.0.1:8080:8080, 8081:8081

Sensitive environment keys discovered from `.env.example`: BINANCE_API_KEY, BINANCE_API_SECRET, CONTEXT7_API_KEY, DASHBOARD_API_KEY, DASHBOARD_API_SECRET, DASHBOARD_WRITE_AUTH_TOKEN, MONGODB_DATABASE, MONGODB_URI, MONGO_INITDB_ROOT_PASSWORD, MONGO_INITDB_ROOT_USERNAME, TELEGRAM_TOKEN

## Assets And Threat Actors

Primary assets:
- Binance credentials (trading and dashboard read-only keys)
- Trading signals, order history, and risk parameters
- MongoDB stored operational data and audit events
- GitHub workflows and repository integrity

Threat actors:
- External attacker probing exposed endpoints and weak auth paths
- Insider or compromised workstation with repository/env access
- Supply-chain attacker via dependencies or CI workflow abuse
- Credential thief targeting Binance or MongoDB secrets

## Prioritized Threats (STRIDE)

- T1 / Spoofing / High
  - Threat: stolen API keys used to submit unauthorized trading actions.
  - Impact: financial loss and account compromise.
  - Mitigations: restrict API scopes, enforce IP whitelist, rotate keys, monitor auth failures.
- T2 / Tampering / High
  - Threat: unauthorized changes to risk logic or order flow through repo or CI manipulation.
  - Impact: silent strategy drift and unsafe execution.
  - Mitigations: branch protection, required reviews, and CI checks on risk modules.
- T3 / Repudiation / Medium
  - Threat: missing audit trace for position or order interventions.
  - Impact: forensic gap after incidents.
  - Mitigations: structured event logging with immutable timestamps and actor/source fields.
- T4 / Information Disclosure / High
  - Threat: secrets leaked in logs, env files, or debug output.
  - Impact: key compromise and data exfiltration.
  - Mitigations: secret scanning, redaction guards, and least-privilege credentials.
- T5 / Denial Of Service / Medium
  - Threat: API/dashboard overload or unstable upstream dependencies.
  - Impact: trading blind spots and stale risk view.
  - Mitigations: timeouts, retries with backoff, health endpoints, graceful degradation.
- T6 / Elevation Of Privilege / High
  - Threat: over-privileged dashboard/API credentials enabling trading privileges.
  - Impact: expanded blast radius from UI/API compromise.
  - Mitigations: separate read-only dashboard keys and strict credential separation.

## Required Follow-up Actions

- Validate T1/T4 controls with `security-audit` before each release.
- Add explicit checklist item for dashboard credential scope verification.
- Ensure CI failure triage flow (`gh-fix-ci`) is part of incident response.
- Re-generate this model after major architecture or deployment changes.
