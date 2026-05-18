# Canonical Pack Knowledge - governance.iniciar

## Status

Canonical shared knowledge (project-applied) near Davi specification.

## Governance Rule

- Commodity enable/disable changes require:
  - explicit human approval in SDD stage gate
  - lint gate `PASS`
  - persisted evidence

## Auditability Rule

- Every approved change must keep:
  - cycle id
  - approver
  - changed commodity status
  - result evidence

## Traceability

- Cycle id: `v2026.05-cycle1-commodities-toggle`
- Origin evidence:
  - `docs/sdd-cycles/v2026.05-cycle1-commodities-toggle/approvals.md`

## Canonical RF/RNF Baseline (SPEC-001)

Source:

- `docs/sdd-cycles/v2026.05-cycle1-commodities-toggle/04-specs.md`

Functional baseline:

- RF-01: manter fonte oficial de habilitacao/desabilitacao de commodities.
- RF-02: validar habilitacao no `INICIAR.BAT` antes da execucao real.
- RF-03: validar habilitacao no `INICIAR_RL.BAT` antes da execucao real.
- RF-04: bloquear commodity desabilitada com mensagem explicita em log/console.
- RF-05: permitir alteracao de status por interface operacional definida.
- RF-06: registrar evidencia de mudanca (quem/quando/o que).

Non-functional baseline:

- RNF-01: erro de configuracao deve resultar em fail-closed.
- RNF-02: preservar baseline inicial `XTIUSD`, `XBRUSD`, `XNGUSD`.
- RNF-03: logs de bloqueio/auditoria devem ser legiveis e rastreaveis por ciclo.
- RNF-04: artefatos alterados devem passar lint gate `PASS`.
- RNF-05: RF/RNF promovidos sao canônicos e nao podem ser quebrados sem
  aprovacao formal.
