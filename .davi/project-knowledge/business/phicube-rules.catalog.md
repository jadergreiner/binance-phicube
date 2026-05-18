# PhiCube Rules Catalog (Parsed from PDF)

## Source

- PDF: `docs/phicube_combined_standalone.pdf`
- Extracted text: `docs/phicube_combined_standalone.extracted.txt`
- Parsing date: `2026-05-17`

## Rule Table

| Rule ID | Description | Artifacts Impacted | Source Pages |
| --- | --- | --- | --- |
| RN-PHI-001 | Use `Phi^3 ~= 4.236` as reference ratio for relative wave sizing between trend and correction. | `signal explanation`, `strategy interpretation`, `SPEC` | 1, 9 |
| RN-PHI-002 | Use fractal `5-3` structure (5 impulsive, 3 corrective) across time scales. | `market structure analysis`, `SPEC` | 2, 9 |
| RN-PHI-003 | Classify `strong uptrend` when three related fractals are ascending together. | `trend classifier`, `risk status`, `explanation` | 2, 9-10 |
| RN-PHI-004 | Classify `strong downtrend` when three related fractals are descending together. | `trend classifier`, `risk status`, `explanation` | 2, 10 |
| RN-PHI-005 | Classify `consolidation/counter-trend` when at least one fractal diverges from the others. | `no-signal logic`, `explanation`, `risk status` | 2, 10 |
| RN-PHI-006 | MIMA ascending alignment (smaller periods above larger periods) indicates bullish trend context. | `indicator interpretation`, `entry filter`, `explanation` | 4, 6, 10 |
| RN-PHI-007 | MIMA descending alignment indicates bearish trend context. | `indicator interpretation`, `entry filter`, `explanation` | 4, 6, 10 |
| RN-PHI-008 | Touch/cross between shorter and longer MIMA can indicate possible reversal point. | `reversal warning`, `risk status`, `explanation` | 6 |
| RN-PHI-009 | SANTO positive/green indicates buying strength; negative/red indicates selling strength. | `momentum classifier`, `entry filter`, `explanation` | 4, 6, 10 |
| RN-PHI-010 | MIMA_ROC above zero indicates upward slope; below zero indicates downward slope. | `trend confirmation`, `entry filter`, `explanation` | 4, 6, 10 |
| RN-PHI-011 | When SANTO and MIMA_ROC agree in sign, trend strength is higher; divergence suggests consolidation/reversal risk. | `confidence score`, `no-signal logic`, `explanation` | 6 |
| RN-PHI-012 | Santo Banda green + aligned MIMAs increases continuation confidence; red indicates opposite context. | `confidence layer`, `risk status`, `explanation` | 5, 6, 10 |
| RN-PHI-013 | MIMASAR represents dynamic support/resistance from trend/consolidation states. | `entry/stop/target calculation`, `explanation` | 4, 6, 10 |
| RN-PHI-014 | Analyze at least three timeframes/fractal orders (smaller/intermediate/larger) before decision. | `analysis pipeline`, `pre-trade checklist` | 6 |
| RN-PHI-015 | Long setup requires: 3 key MIMAs aligned up, SANTO positive, MIMA_ROC > 0, price above support (MIMASAR). | `long setup gate`, `task contracts`, `tests` | 7 |
| RN-PHI-016 | Short setup requires: descending MIMA alignment, SANTO negative, MIMA_ROC < 0, price below resistance. | `short setup gate`, `task contracts`, `tests` | 7 |
| RN-PHI-017 | Long stop should be set below the immediate higher-order MIMA or nearest support line. | `risk management`, `order builder` | 7 |
| RN-PHI-018 | Short stop should be set above the higher-order MIMA or nearest resistance line. | `risk management`, `order builder` | 7 |
| RN-PHI-019 | If smaller fractal starts diverging against position, reduce exposure or increase caution. | `position management`, `risk status`, `explanation` | 7 |
| RN-PHI-020 | Adjust stops as price stretches from MIMAs and use MIMASAR lines as partial targets. | `trade management`, `explanation` | 7 |
| RN-PHI-021 | Exit when MIMAs cross against trade direction or when SANTO indicates loss of force. | `exit logic`, `explanation` | 7 |
| RN-PHI-022 | In prolonged consolidation, allow partial exit and wait for new alignment before re-entry. | `consolidation handling`, `no-signal logic` | 7 |
| RN-PHI-023 | Operate only with risk capital; never allocate full capital to trading operations. | `governance policy`, `risk controls` | 5, 8, 11 |
| RN-PHI-024 | Signals from app/Prisma must be confirmed on charts before order execution. | `signal validation gate`, `execution checklist` | 8 |
| RN-PHI-025 | Connectivity/third-party platform issues are operational risks that can affect order/information integrity. | `runtime safeguards`, `incident playbook` | 5, 11 |

## Notes

- This pack captures public methodological and operational rules from source text.
- Proprietary formulas (exact MIMA/MIMASAR internals) are intentionally unknown and must not be inferred as factual.
