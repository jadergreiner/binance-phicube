# SPEC_044 — Circuit Breaker Preditivo (Slippage Antecipado)

**ID:** SPEC_044
**Status:** Rascunho
**Data:** 2026-05-12
**Versão:** 1.0
**Dependências:** SPEC_043 (Slippage Protection, priceProtect, Circuit Breaker Reativo)
**Skill de validação:** `sdd-spec-driven-development`, `qa-review`, `signal-review`

---

## 1. Título e Resumo

### 1.1 Nome da Funcionalidade

Circuit breaker preditivo — bloqueio antecipado de pares de baixa liquidez em condições adversas de mercado

### 1.2 Resumo

**O que é:** Extensão do circuit breaker implementado em SPEC_043. Enquanto o SPEC_043 opera de forma **reativa** (responde a perdas já ocorridas), este SPEC adiciona uma camada **preditiva** que avalia as condições de mercado *antes* da entrada e pode pular o ciclo do par se a relação volatilidade/liquidez estiver em níveis perigosos.

**Por que estamos fazendo:** Análise forense mostrou que o outlier CHZUSDT (−$16,42) poderia ter sido evitado se o sistema tivesse identidicado que a relação ATR/preço + baixa liquidez naquele momento tornava o slippage esperado superior ao risco aceitável — antes da entrada.

**Valor de negócio:** Prevenir perdas por slippage antes delas acontecerem, em vez de apenas reduzir o risco depois da primeira perda.

**Conexão com SPEC_043:** SPEC_043 implementa o modelo de slippage (`_estimate_slippage`) e o circuit breaker reativo. SPEC_044 usa a mesma infraestrutura (tiers de liquidez, cálculo de slippage) para uma gate de entrada preditiva.

---

## 2. Objetivos e Escopo

### 2.1 Objetivos

- [ ] P1: Implementar gate de entrada preditiva no `SignalEngine.evaluate()` ou no `RiskManager.calculate()` que avalie a relação `ATR/price` vs `slippage_tier` antes de aprovar o trade
- [ ] P2: Definir percentil histórico do ATR como gatilho — se ATR/p > percentil 85 dos últimos 100 candles + tier "low" → pular ciclo
- [ ] P3: Log estruturado com `predictive_circuit_breaker_skipped` contendo métricas
- [ ] P4: Métrica de dashboard: "trades skipped by predictive circuit breaker"

### 2.2 Fora do Escopo

- **Não inclui:** ML model training (o percentil histórico é suficiente)
- **Não inclui:** Persistência de estado entre restart do bot (recalcula percentil a cada fetch)
- **Não inclui:** Implementação sem SPEC_043 — este SPEC depende da infraestrutura de tiers e slippage

---

## 3. Design e Arquitetura

### 3.1 Critério de Ativação

```
skip_cycle = (
    par_liq_tier == "low"
    AND atr_ratio > percentile_85_of_last_100
)
```

Onde:
- `par_liq_tier` = `backtest_slippage_liq_map.get(symbol, "medium")` (reutilizado de SPEC_043)
- `atr_ratio` = `atr_value / close_price` (volatilidade relativa atual)
- `percentile_85` = percentil 85 do `atr_ratio` na janela dos últimos 100 candles

### 3.2 Localização

O gate deve ficar no `RiskManager.calculate()`, como um GATE adicional ANTES do cálculo de position size:

```
calculate(signal, balance, df):
  │
  ├─ [GATE 0] intraday loss limit check (existente)
  ├─ [GATE 0.5] PREDICTIVE CIRCUIT BREAKER (NOVO)
  │    └─ Se atr_ratio > p85 AND tier == "low" → skip
  │
  ├─ [GATE 1] stop_distance check (existente)
  ...
```

### 3.3 Método `_predictive_circuit_breaker()`

```python
def _predictive_circuit_breaker(
    self,
    symbol: str,
    atr_value: float,
    close_price: float,
    df_atr_history: pd.Series,  # série histórica do ATR ratio
) -> bool:
    """Retorna True se o ciclo deve ser pulado."""
    tier = self._liq_map.get(symbol, "medium")
    if tier != "low":
        return False  # só avalia para pares de baixa liquidez

    current_atr_ratio = atr_value / close_price if close_price > 0 else 0
    percentile_85 = df_atr_history.quantile(0.85)

    if current_atr_ratio > percentile_85:
        logger.warning(
            "predictive_circuit_breaker_skipped",
            symbol=symbol,
            tier=tier,
            atr_ratio=round(current_atr_ratio, 6),
            percentile_85=round(percentile_85, 6),
        )
        return True

    return False
```

### 3.4 Arquivos Afetados

| Arquivo | Mudança |
|---|---|
| `src/trading/risk_manager.py` | Novo método `_predictive_circuit_breaker()`, gate em `calculate()` |
| `src/monitoring/logger.py` | Novo evento `predictive_circuit_breaker_skipped` (opcional) |
| `src/config/settings.py` | Pode adicionar `predictive_breaker_percentile: float = 0.85` e `predictive_breaker_tiers: list[str] = ["low"]` |

---

## 4. Testes

| ID | Descrição | Prioridade |
|---|---|---|
| TEST-044-01 | Par tier "low" com ATR ratio > p85 → skip=True | Alta |
| TEST-044-02 | Par tier "low" com ATR ratio <= p85 → skip=False | Alta |
| TEST-044-03 | Par tier "high" com ATR ratio > p85 → skip=False (não avalia low) | Alta |
| TEST-044-04 | Par desconhecido (fallback "medium") com ATR > p85 → skip=False | Média |
| TEST-044-05 | Log estruturado emitido quando skip=True | Média |
| TEST-044-06 | Métrica de dashboard "skipped_by_predictive_breaker" | Média |

---

## 5. Definição de Pronto

- [ ] P1 implementado e testado
- [ ] TEST-044-01 a 06 passando
- [ ] Logs estruturados presentes
- [ ] SPEC_043 já implementado em produção (dependência)
- [ ] 1 semana de dados de produção com SPEC_043 antes de ativar SPEC_044

---

## 6. Dependências

```
SPEC_043 (priceProtect + slippage model + tiers de liquidez + circuit breaker reativo)
  └── SPEC_044 (circuit breaker preditivo)
```

SPEC_044 SÓ deve ser implementada após SPEC_043 estar em produção por no mínimo 1 semana.

---

## 7. Notas

- Este documento é um rascunho inicial para direcionamento do Time B.
- O percentil 85 é um chute inicial — pode ser ajustado via backtest histórico.
- A validação de negócio (quantos trades seriam pulados, qual o impacto no PnL) deve ser feita pelo Time B antes da implementação.

---

## Histórico

- **2026-05-12:** Criação da SPEC_044 — proposta pelo ML/AI Engineer durante refinamento do SPEC_043. Decisão do Arquiteto: documentar como follow-up.
