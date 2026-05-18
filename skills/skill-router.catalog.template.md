<!-- markdownlint-disable MD013 -->

# Skill Router Catalog Template

Use this catalog to define auto-activation signals per skill.

## Fields

- `skill_id`: folder name under `core/skills/<domain>/`.
- `domain`: `engineering`, `misc`, `personal`, or `productivity`.
- `status`: `implemented` or `scaffold`.
- `paths`: allowed flow paths (`Q&A`, `RCA`, `New Implementation`).
- `trigger_signals`: keywords or explicit intents.
- `impact_level`: `low`, `medium`, `high`.
- `requires_human_gate`: `true` or `false`.
- `fallback`: behavior when not implemented.

## Baseline catalog

| skill_id | domain | status | paths | trigger_signals | impact_level | requires_human_gate | fallback |
| --- | --- | --- | --- | --- | --- | --- | --- |
| diagnose | engineering | implemented | RCA | bug, erro intermitente, causa raiz, regressao | high | true | keep RCA flow with evidence checkpoints |
| tdd | engineering | scaffold | New Implementation, RCA | testes antes do codigo, red green refactor | medium | false | suggest skill and keep executor checklist |
| grill-with-docs | engineering | scaffold | Q&A, New Implementation | alinhar termos, contexto, ADR, contexto de dominio | medium | true | run refiner business/architecture/governance |
| improve-codebase-architecture | engineering | scaffold | New Implementation, RCA | refatoracao estrutural, arquitetura, limites de modulo | high | true | route to architecture refiner with trade-off gate |
| triage | engineering | scaffold | RCA, Q&A | priorizar bugs, severidade, impacto | medium | false | use governance prioritization rules |
| zoom-out | engineering | scaffold | Q&A, New Implementation | visao sistemica, macro, roadmap tecnico | low | false | continue with normal guided conduction |

## Consumer overrides

Consumers should copy this file and maintain active entries under:

- `.davi/skill-router.overrides.yaml`

Core keeps the canonical template only.
