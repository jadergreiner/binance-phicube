# Relatório de Calibração do atr_multiplier

**Data:** 2026-05-11
**Contexto:** SPEC_029 — Position Sizing por ATR

## Parâmetros da Simulação

| Parâmetro | Valor |
|-----------|-------|
| Pares | BTCUSDT, BROCCOLI714USDT, XAUUSDT, QNTUSDT, SOLUSDT |
| Período | 30 dias (2026-04-11 a 2026-05-11) |
| Timeframe | 15m |
| ATR Period | 14 |
| Multiplier Range | 1.0 a 5.0 (step 0.5) |
| Fractal SL estimate | 1.5× TR mean |
| Total candles/par | 2.892 (~2.878 válidos pós-ATR) |

## Resultados por Multiplier

### atr_multiplier = 1.5 (default inicial do SPEC)

| Par | guard_activation_pct | atr_dominance_pct |
|-----|---------------------|-------------------|
| BTCUSDT | 53.6% | 46.4% |
| BROCCOLI714USDT | 65.5% | 34.5% |
| XAUUSDT | 41.2% | 58.8% |
| QNTUSDT | 51.9% | 48.1% |
| SOLUSDT | 55.4% | 44.6% |

**Análise:** Guard ativo ~50-65% do tempo — position sizing ainda muito próximo do fixed mode. O ATR raramente domina o sizing.

### atr_multiplier = 2.0 ★ **RECOMENDADO**

| Par | guard_activation_pct | atr_dominance_pct |
|-----|---------------------|-------------------|
| BTCUSDT | 25.4% | 74.6% |
| BROCCOLI714USDT | 45.8% | 54.2% |
| XAUUSDT | 31.5% | 68.5% |
| QNTUSDT | 20.5% | 79.5% |
| SOLUSDT | 24.4% | 75.6% |

**Análise:** ATR domina 54-80% do tempo. Guard atua apenas quando a volatilidade está excepcionalmente baixa (fractal > ATR×2). Balança segurança (fractal como piso) com adaptação à volatilidade (ATR). **Ponto ótimo.**

### atr_multiplier = 3.0

| Par | guard_activation_pct | atr_dominance_pct |
|-----|---------------------|-------------------|
| BTCUSDT | 9.9% | 90.1% |
| BROCCOLI714USDT | 22.8% | 77.2% |
| XAUUSDT | 29.1% | 70.9% |
| QNTUSDT | 2.6% | 97.4% |
| SOLUSDT | 6.5% | 93.5% |

**Análise:** ATR domina quase sempre. Guard raramente ativo — posições podem ficar muito pequenas em volatilidade alta. Agressivo demais para default.

## Recomendações

### Multiplier Global: **2.0**

Justificativa:
1. **Ponto de inflexão:** em 2.0, o ATR domina o guard na maioria dos pares (54-80%)
2. **Proteção preservada:** guard ainda ativo em 20-46% dos candles — fractal continua sendo o piso
3. **Consistência entre pares:** comportamento homogêneo exceto BROCCOLI714 (mais guard) — mas dentro do aceitável
4. **INV-029-05:** risk_overshoot_p95 = 1.0 para todos os multipliers (inerente ao modelo atr_with_guard, sem overshoot por construção)

### Override por Par

| Par | Recomendação | Motivo |
|-----|-------------|--------|
| BTCUSDT | Default (2.0) | Comportamento padrão |
| BROCCOLI714USDT | Default (2.0) | Guard 45.8% em 2.0 — aceitável, não justifica override |
| XAUUSDT | **3.0** | Guard ainda 26.4% em 4.0 — ouro tem baixa volatilidade intrínseca. Multiplier maior compensa sem perder proteção |
| QNTUSDT | Default (2.0) | Comportamento padrão |
| SOLUSDT | Default (2.0) | Comportamento padrão |

### RISK_PER_TRADE_USDT

Com saldo atual de **$300** e `RISK_PER_TRADE_USDT=5.0` (1.67% do saldo):
- Posição mínima segura para BTCUSDT a $60k: `$5 × 60000 / (max(fractal, ATR×2))`
- ATR(14) de BTCUSDT em 15m ~$300 → effective_stop ~$600 → position ~$500 → viável
- Pares de menor preço (QNT a $70): position ~$5 × 70 / stop → viável mesmo com stop $5+

**RISK_PER_TRADE_USDT = 5.0** confirmado como default adequado para saldo $300.

## Artefatos

- `calibracao_atr_multiplier.csv` — Dados completos da simulação
- `calibracao_atr_multiplier.png` — Gráfico guard_activation_pct vs multiplier
- `calibracao_relatorio.md` — Este relatório

## Conclusão

**atr_multiplier=2.0** com override `ATR_MULTIPLIER_XAUUSDT=3.0`. Default global 2.0 já produz ~70-80% de dominância ATR nos pares principais, com guard ativo apenas em baixa volatilidade — exatamente o comportamento desejado do modelo `atr_with_guard`.
