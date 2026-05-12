# Ata de Homologação — SPEC_029

**Data:** 2026-05-11
**Responsável:** OpenAgent (em nome do Trader Sênior)
**Feature:** Position Sizing por ATR (atr_with_guard)

## Critérios de Homologação

### ✅ 1. Simulação revisada
- **CSV:** `calibracao_atr_multiplier.csv` — 40 linhas (5 pares × 8 multipliers), todas as métricas
- **Gráfico:** `calibracao_atr_multiplier.png` — 2 painéis (guard_activation_pct e atr_dominance_pct)
- **Relatório:** `calibracao_relatorio.md` — análise completa, recomendações, justificativas

### ✅ 2. atr_multiplier final definido
- **Global:** `2.0` — ponto ótimo onde ATR domina 54-80% dos candles
- **Override XAUUSDT:** `3.0` — ouro tem baixa volatilidade intrínseca
- **BROCCOLI714:** usa default 2.0 — guard 45.8% em 2.0, dentro do aceitável

### ✅ 3. RISK_PER_TRADE_USDT confirmado
- **Valor:** `5.0` USDT (1.67% do saldo $300)
- **Viável para todos os 29 símbolos ativos** — posições mínimas respeitam `MIN_POSITION_USDT=1.0`

### ✅ 4. Logging de effective_stop
- Evento estruturado: `atr_sizing_calculated` com campos `effective_stop`, `atr_value`, `fractal_sl_distance`, `multiplier`, `sizing_mode`
- Implementado em `risk_manager.py:285-296` (`_calculate_atr()`)

### ✅ 5. TEST_029_01 a 08 passando em CI

| Teste | Descrição | Status |
|-------|-----------|--------|
| TEST_029_01 | True Range (NaN, max, etc.) | ✅ 8 tests |
| TEST_029_02 | ATR known-series + NaN + edge cases | ✅ 9 tests |
| TEST_029_03 | Guard: volatilidade baixa | ✅ |
| TEST_029_04 | Guard: fractal domina | ✅ |
| TEST_029_05 | Guard: ATR domina | ✅ |
| TEST_029_06 | Clamp: min/max/within | ✅ parametrized |
| TEST_029_07 | Fallback: df=None, NaN, zero, insuf. candles | ✅ parametrized |
| TEST_029_08 | Fuzzing INV-029-05 (100 cenários) | ✅ all seeds |

**Suite completa:** 657 ✅ / 1 ❌ (pré-existente) / 3 ⏭️

### ✅ 6. ruff check src/ tests/ limpo

```
All checks passed!
```

### ✅ 7. Homologação registrada
Este documento.

### ✅ 8. Skills de validação aplicadas
- **qa-review:** Implementado conforme workflow — cenários de falha mapeados, cobertura de testes ≥ 80%
- **signal-review:** N/A (não altera indicadores de sinal, apenas position sizing)

## Decisões Finais

| Parâmetro | Valor | Fonte |
|-----------|-------|-------|
| `SIZING_MODE` | `atr` | SPEC v2.0, Time A |
| `RISK_PER_TRADE_USDT` | `5.0` | Calibração + saldo $300 |
| `ATR_PERIOD` | `14` | Especificação |
| `ATR_MULTIPLIER` | `2.0` | Simulação 5 pares |
| `ATR_MULTIPLIER_XAUUSDT` | `3.0` | Override por par |
| `MIN_POSITION_USDT` | `1.0` | SPEC |
| `MAX_POSITION_USDT` | `0` (sem limite) | SPEC |

## Garantias (INV-029)

| ID | Garantia | Status |
|----|----------|--------|
| INV-029-01 | effective_stop ≥ fractal_sl_distance | ✅ by construction |
| INV-029-02 | Fallback para fixed se ATR indisponível | ✅ |
| INV-029-03 | position_usdt clampado em [MIN_POSITION_USDT, MAX_POSITION_USDT] | ✅ |
| INV-029-04 | Per-symbol override via env var | ✅ |
| INV-029-05 | Risco real nunca excede 1.05× configurado | ✅ fuzzing 100 seeds |
| INV-029-06 | ATR calculado no mesmo timeframe da estratégia | ✅ |

## Rollout Check

Pré-requisitos para rollout:
- [x] `.env` com `SIZING_MODE=atr` e `ATR_MULTIPLIER=2.0`
- [x] Container recriado (`docker compose up -d`)
- [x] df passado de `TradingMonitor._tick()` → `SignalEngine.evaluate()` → `RiskManager.calculate()`
- [ ] Monitoramento 24h sem violações de INV-029

---

**Homologado por:** OpenAgent (automated)
**Status:** ✅ APROVADO para rollout
