# Compliance Matrix - SPEC_021

Status values: `pass`, `fail`, `pending`.

| requirement_id | source_ref | test_ref | status | evidence_ref | notes |
|---|---|---|---|---|---|
| REQ-SIG-001 | PRD.md (Signal Engine acurado) + docs/SDD/SPEC.md §2.1 | tests/test_signal_engine.py | pass | tests/test_signal_engine.py | Base signal logic covered. |
| REQ-SIG-002 | docs/SDD/SPEC.md §2.1 (corpus validation) | tests/strategy/test_signal_engine_corpus.py | pass | tests/strategy/test_signal_engine_corpus.py | SPEC_013 corpus suite exists. |
| REQ-RISK-001 | PRD.md (Risk Manager preciso) + docs/SDD/SPEC.md §2.2 | tests/trading/test_risk_manager.py | pass | tests/trading/test_risk_manager.py | Dedicated suite added; gate threshold satisfied. |
| REQ-ORD-001 | PRD.md (Order Manager reliability) + docs/SDD/SPEC.md §2.3 | tests/notifications/test_integration.py | pass | tests/notifications/test_integration.py | Core order flow mocked with notifier integration. |
| REQ-ORD-002 | docs/SDD/SPEC.md §2.3 (rollback on SL/TP failure) | tests/trading/test_order_manager.py | pass | tests/trading/test_order_manager.py | Explicit SL/TP failure rollback scenarios covered with `cancel_all_orders` assertion. |
| REQ-OPS-001 | PRD.md (Health/resilience) + docs/SDD/SPEC.md §1.3/1.4 | tests/api/test_health_endpoint.py; tests/api/test_health_bot_process.py | pass | tests/api/test_health_endpoint.py | Health endpoint behavior is covered. |
