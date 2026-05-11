# Changelog

Todas as mudanças notáveis neste projeto serão documentadas neste arquivo.

## [Unreleased] — 2026-05-11

### Feat (SPEC_030 — Saída Dinâmica)

- **TP Parcial (V1):** Implementação de take-profit escalonado com até 3 níveis configuráveis via ordens `TAKE_PROFIT_MARKET` reduceOnly nativas. Zero lógica de pós-processamento — a exchange gerencia o ajuste automático das ordens remanescentes.
- **Trailing Stop (V2):** Implementação de `TRAILING_STOP_MARKET` via Algo Order API com `activatePrice` e `callbackRate` configuráveis. Substitui o SL fixo quando ativo.
- **ExitStrategy:** Novo enum com suporte a `fixed` (legado), `partial` (TP escalonado) e `trailing` (trailing stop nativo).
- **Config validation:** Startup fatal para configuração inválida (níveis TP fora de 1..3, `sum(qty_pct) > 100`, `activation_pct <= callback_rate`).
- **RRR ponderado:** Cálculo de Risk/Reward Ratio médio ponderado pela quantidade de cada nível TP.
- **SimulatedClient:** Suporte a N ordens reduceOnly simultâneas com `check_and_execute_conditional_orders()`.
- **Testes:** 15 cenários (12 V1 + 3 V2) cobrindo execução, rollback, validação de configuração e integração simulada.

### Fix

- **Testes:** Correção de mock MongoDB (`test_setup_indexes_respeita_retencao_minima_90_dias`) para incluir coleção `customers`.

### Docs

- `docs/SDD/SPEC_030_SAIDA_DINAMICA/SPEC.md` — especificação técnica versão 2.0
- `docs/SDD/SPEC_030_SAIDA_DINAMICA/refinamento-2026-05-11.md` — 8 decisões (D-001 a D-008)

## Anteriores

### 2026-05-10

- **feat(sizing):** Implementação de position sizing baseado em ATR (SPEC_029) com fallgrace para o modelo fixo.
- **feat(backtest):** Backtesting realista com slippage, taxas e dimensionamento via RiskManager.
- **refactor(code-quality):** Correção de imports não utilizados, migração de 3 enums para `StrEnum`, formatação `ruff`.
- **docs(agents):** Consolidação do `AGENTS.md` com o código atual.
- **docs(sdd):** Adição de SPEC_028-036 para roadmap de evolução.
- **fix(docker):** Correção de `PermissionError` no diretório de logs e refatoração de Dockerfiles.
- **feat:** Adição de tabela MCP-PoS Customer à Dashboard API.
